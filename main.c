//******************************************************************************
// * File:    main.c
// * Device:  TMS320F280015x (or similar)
// *
// * Purpose:
// *   - Initializes system, SCIA (Master), and SCIB (ACU).
// *   - Uses Timer2 to count system time with a 1 ms tick.
// *   - Every 10 ms, Timer2 ISR triggers master transmission via uartMsgTxMaster().
// *   - Every 100 ms, Timer2 ISR triggers ACU transmission via uartMsgTxACU(), but only if enabled.
// *   - ACU transmission is enabled after 1000 seconds (1,000,000 ms).
// *   - When systemTimeCounter reaches 60,000 ms (60 seconds), a flag is set.
// *   - The main loop can check flags and process data as needed.
// *
// * Note:
// *   - Timer0 and Timer1 functionalities have been removed to consolidate timing on Timer2.
// *   - Both uartMsgTxMaster() and uartMsgTxACU() are triggered from the Timer2 ISR.
// ******************************************************************************/

#include "device.h"
#include "driverlib.h"
#include "board.h"
#include "timers.h"
#include "uart_operation_master.h"
#include "uart_operation_acu.h"
#include "globals_and_gpio.h"
#include "filters.h"
#include "globals_and_gpio.h"
#include "accelerometer.h"

//#include "c28x_core_registers.h"
volatile uint32_t SystemTime = 0;
volatile bool filtred_p3v3_ok = false;
volatile bool filtred_safety_pin = false;
volatile bool filtred_comOkMaster = false;
volatile bool filtred_comOkACU = false;
volatile bool filtred_hvCup_safe = false;
volatile bool filtred_hvCup_armed = false;
volatile bool filtred_comOkI2C = false;
volatile bool masterTxDue = false;
volatile bool acuTxDue    = false;
void defaultFiltersAndTimers(void)
{
    SystemTime = 0;
    resetSystemTimer();
    masterLastPacketTime = 0;
    acuLastPacketTime = 0;
    filtred_safety_pin = false;
    filtred_p3v3_ok = false;
    filtred_comOkMaster = false;
    filtred_comOkACU = false;
    filtred_comOkI2C = false;
}

void main(void)
{

    Current_state = PBIT;
    //---------------------------------------------------------------------
    // 1) Basic device init (clocks, watchdog, GPIOs)
    //---------------------------------------------------------------------
    SysCtl_disableWatchdog();
    Board_init();
    Device_init();
    Device_initGPIO();
    setupGPIOs();

    //---------------------------------------------------------------------
    // 2) Initialize interrupt module & vector table
    //---------------------------------------------------------------------
    Interrupt_initModule();
    Interrupt_initVectorTable();
    //---------------------------------------------------------------------
    // 3) Initialize system timer (Timer2)
    //---------------------------------------------------------------------
    initSystemTimer();
    initGclkEPWM();
    //---------------------------------------------------------------------
    // 4) Initialize UART modules for Master (SCIA) and ACU (SCIB)
    //---------------------------------------------------------------------
    uartConfigMaster();  // Master: SCIC pins: 6=RX, 4=TX

    uartConfigACU();     // ACU:    SCIB pins: 13=RX, 12=TX
    //accelerometer_init();
    stopGclk();
    //---------------------------------------------------------------------
    // 5) Enable global interrupts
    //---------------------------------------------------------------------
    EINT;   // Enable CPU interrupts
    ERTM;   // Enable real-time debug interrupt


    // Set default output levels
    GPIO_writePin(SW1_2EN, 0);
    GPIO_writePin(GCLK_TO_MCU2, 0);
    GPIO_writePin(TRIG_P, 0);
    GPIO_writePin(TRIG_N, 1);

    resetSystemTimer(); // Reset the timer
    // Wait until 1000 seconds (1,000,000 ms) have elapsed before enabling ACU TX
    while(SystemTime < WAKE_UP)
    {
        SystemTime = getSystemTime();
    }
    acuEnableTx = true;
    resetSystemTimer(); // Reset the timer

    while(1)
    {


        if (masterTxDue) {
            masterTxDue = false;
            uartMsgTxMaster();
        }
        if (acuTxDue) {
            acuTxDue = false;
            uartMsgTxACU();
        }
        SystemTime = getSystemTime();

        switch (Current_state)
           {
            case PBIT: // 1: Power-on Built-In Test
            {


                if (!filtred_safety_pin){
                    filtred_safety_pin = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P5V_SAFETY_GOOD_ISO, false);
                }

                if (!filtred_p3v3_ok){
                    filtred_p3v3_ok = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P3V3_GOOD, true);
                }
                if(!filtred_comOkMaster){
                    filtred_comOkMaster = checkComOkMaster(FILTER_PROTOCOL);
                }

                if(filtred_p3v3_ok && filtred_comOkMaster && filtred_safety_pin){
                    Current_state = IDNTIF_RFM_FLIGHT_MODULE;
                    filtred_safety_pin = true;
                    defaultFiltersAndTimers();
                }
                else if(SystemTime >= TIMEOUT_PBIT){
                    defaultFiltersAndTimers();
                    Current_state = FAIL_SAFE;
                }
                else{
                    Current_state = PBIT;
                }
            }
            break;

            case IDNTIF_RFM_FLIGHT_MODULE: // 2: Identify RFM - Flight module
            {

                if (!filtred_safety_pin){
                    filtred_safety_pin = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P5V_SAFETY_GOOD_ISO, false);
                }

                // If the received MSP message indicates function 0x84 and both communication and voltage conditions are met, transition to next state.
                if(receivedMsgACU.function_msb == (uint8_t)((IDENTIFY_RFM_ACU >> 8) & 0xFF)
                   && receivedMsgACU.function_lsb == (uint8_t)(IDENTIFY_RFM_ACU& 0xFF)){

                    Current_state = IDNTIF_RFM_ACU;
                    filtred_hvCup_safe = false;
                    defaultFiltersAndTimers();
                }
                // Error check: if hvCup_safe indicates a false condition, transition to FAIL_SAFE.
                else if ((SystemTime - masterLastPacketTime) > TIMEOUT_COMMUNICATION
                        || (SystemTime - acuLastPacketTime) > TIMEOUT_COMMUNICATION){
                    Current_state = FAIL_SAFE;
                }
                else{
                    Current_state = IDNTIF_RFM_FLIGHT_MODULE;
                }
            }
            break;

           case IDNTIF_RFM_ACU: // 3:
           {
               if (!filtred_safety_pin){
                   filtred_safety_pin = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P5V_SAFETY_GOOD_ISO, false);
               }

               if(!filtred_comOkACU){
                   filtred_comOkACU = checkComOkACU(FILTER_PROTOCOL);
               }
               // At slave, send status each 1 sec (1Hz) -> Receive message 3.4.2.2 #39899128,
               // update decodeMspV2Message OSD Message with function 0x3004 if ACU OK and identification data received.
               // Check if master communication is OK (requires at least 5 master packets).
               if (!filtred_comOkMaster){
                   filtred_comOkMaster = checkComOkMaster(FILTER_PROTOCOL);
               }
               // Process the received MSP message.
               //TODO add: sync_acu_done & acu_ok
               if(receivedMsgACU.function_msb == (uint8_t)((IDENTIFY_RFM_ACU >> 8) & 0xFF)
                  && receivedMsgACU.function_lsb == (uint8_t)(IDENTIFY_RFM_ACU& 0xFF
                  && filtred_comOkMaster)){
                    Current_state = READY_FOR_SAFETY_PIN; // Transition to READY state
                    filtred_safety_pin = true;
                    defaultFiltersAndTimers();
               }
               // If the safety condition is not acceptable, transition to FAIL_SAFE.
               else if (!filtred_safety_pin){
                    Current_state = FAIL_SAFE;
               }
               else{
                   Current_state = IDNTIF_RFM_ACU;
               }
           }
           break;

           case READY_FOR_SAFETY_PIN: // 4: System Ready for safety pin
           {
               // Send status each 1 sec (1Hz) -> Receive message 3.4.2.2 #39899128 from state.
               // Send OSD message with function 0x3004 updating payload "ready for remove safety pin".

               filtred_safety_pin = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P5V_SAFETY_GOOD_ISO, false);

               //if(!filtred_comOkI2C){
               //    filtred_comOkI2C = checkComOkI2C(FILTER_PROTOCOL);
               //}

               if(!filtred_comOkACU){
                   filtred_comOkACU = checkComOkACU(FILTER_PROTOCOL);
               }
               //TODO add filtred_comOkI2C
               //if (filtred_comOkACU && !filtred_safety_pin){
               if (filtred_comOkACU && filtred_safety_pin){
                   Current_state = ARM_DELEY;
                   filtred_safety_pin = false;
                   defaultFiltersAndTimers();
               }
               //TODO add (SystemTime - i2cLastPacketTime) > TIMEOUT_COMMUNICATION
               else if ((SystemTime - masterLastPacketTime) > TIMEOUT_COMMUNICATION || (SystemTime - acuLastPacketTime) > TIMEOUT_COMMUNICATION)  // 15 seconds
               {
                   Current_state = FAIL_SAFE;
               }
               else{
                   Current_state = READY_FOR_SAFETY_PIN;
               }
           }
           break;

           case ARM_DELEY: // 5: Arming State
           {
               // Send status each 1 sec (1Hz) -> Receive message 3.4.2.2 #39899128 from state.
               // Send OSD message with function 0x3004 updating payload "ready for remove safety pin".
               filtred_safety_pin = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P5V_SAFETY_GOOD_ISO, false);

               if (filtred_safety_pin){
                   Current_state = READY_FOR_SAFETY_PIN; // Transition to READY_FOR_SAFETY_PIN
                   defaultFiltersAndTimers();
               }

               else if (!filtred_safety_pin && (SystemTime >= TIMEOUT_ARM_DELEY)) {
                   Current_state = WAIT_FOR_ARM; // Transition to WAIT_FOR_ARM
                   filtred_safety_pin = false;
                   defaultFiltersAndTimers();
               }

               //TODO add (SystemTime - i2cLastPacketTime) > TIMEOUT_COMMUNICATION
               else if ((SystemTime >= TIMEOUT_ARM_DELEY) && ((SystemTime - masterLastPacketTime) > TIMEOUT_COMMUNICATION || (SystemTime - acuLastPacketTime) > TIMEOUT_COMMUNICATION)){
                   Current_state = FAIL_SAFE;
               }
               else{
                   Current_state = ARM_DELEY;
               }
           }
           break;

           case WAIT_FOR_ARM: // 6: Waiting for Arm Command
           {
               // Send status each 1 sec (1Hz) -> Receive message 3.4.2.2 #39899128 from state.
               filtred_safety_pin = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P5V_SAFETY_GOOD_ISO, false);
               if (filtred_safety_pin){
                   Current_state = READY_FOR_SAFETY_PIN;
                   defaultFiltersAndTimers();
               }
               else if(receivedMsgACU.function_msb == (uint8_t)((ACU_ARM_COMMAND >> 8) & 0xFF)
                  && receivedMsgACU.function_lsb == (uint8_t)(ACU_ARM_COMMAND& 0xFF)){
                   Current_state = ARMING_HAND_SHAKE;
                   defaultFiltersAndTimers();
               }
               //TODO add (SystemTime - i2cLastPacketTime) > TIMEOUT_COMMUNICATION
               else if ((SystemTime - masterLastPacketTime) > TIMEOUT_COMMUNICATION
                       || (SystemTime - acuLastPacketTime) > TIMEOUT_COMMUNICATION){
                       Current_state = FAIL_SAFE;
               }
               else{
                   Current_state = WAIT_FOR_ARM;
               }
           }
           break;

           case ARMING_HAND_SHAKE: // 7: Handshake During Arming
           {
               if (handShakeOK){
                   Current_state = ARMING;
                   defaultFiltersAndTimers();
               }
               else if (SystemTime >= TIMEOUT_ARM_HANDSHAKE){
                   Current_state = DISARM;
                   defaultFiltersAndTimers();
               }
               else{
                   Current_state = ARMING_HAND_SHAKE;
               }

           }
           break;

           case ARMING: // 8: Arming in Progress
           {
               functionTX = ACU_ARM_COMMAND;
               startGclk();
               GPIO_writePin(SW1_2EN, 1);
               GPIO_writePin(TRIG_P, 0);
               GPIO_writePin(TRIG_N, 1);

               filtred_hvCup_armed = adc_filter(FILTER_GPIO, HV_CUP_ADC_CHANNEL, ARMED_CUP_VOLT, true);

               if (filtred_hvCup_armed){
                   Current_state = ARMED;
                   defaultFiltersAndTimers();
               }
               else if (!filtred_hvCup_armed & SystemTime >= TIMEOUT_ARMING){
                   Current_state = FAIL_SAFE;
               }
               else{
                   Current_state = ARMING;
               }

           }
           break;

           case ARMED: // 9: System Armed
           {
               startGclk();
               GPIO_writePin(SW1_2EN, 1);
               GPIO_writePin(TRIG_P, 0);
               GPIO_writePin(TRIG_N, 1);

               filtred_p3v3_ok = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P3V3_GOOD, true);

               filtred_safety_pin = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P5V_SAFETY_GOOD_ISO, false);
               //TODO add acc if enabled
               //TODO add DIASARM if DISARMD COMMAND or 15 Sec no communication with ACU

               if(acuHeader1 == ACU_DET_COMMAND && acuHeader2 == ACU_DET_COMMAND){
                   defaultFiltersAndTimers();
                   Current_state = DET; // Transition to FAIL_SAFE
               }
               else if (!filtred_p3v3_ok || !filtred_safety_pin){
                   Current_state = FAIL_SAFE; // Transition to FAIL_SAFE
               }
               else{
                   Current_state = ARMED;
               }
           }
           break;

           case DET: // 10: Detection / Detonation
           {
               startGclk();
               GPIO_writePin(SW1_2EN, 1);
               GPIO_writePin(TRIG_P, 1);
               GPIO_writePin(TRIG_N, 0);
               if (SystemTime >= TIMEOUT_DET1_TIMEOUT){
                   GPIO_writePin(TRIG_P, 0);
                   GPIO_writePin(TRIG_N, 1);
                   defaultFiltersAndTimers();
                   Current_state = SEC_DET_ATTEMPT;
               }
               else{
                   Current_state = DET;
               }
           }
           break;

           case DISARM: // 11: Disarm State
           {

               filtred_p3v3_ok = gpio_stability_filter(FILTER_GPIO, FILTER_ACCURACY, P3V3_GOOD, true);
               filtred_hvCup_safe = adc_filter(FILTER_GPIO, HV_CUP_ADC_CHANNEL, SAFETY_CUP_VOLT, false);

               //TODO add (SystemTime - i2cLastPacketTime) > TIMEOUT_COMMUNICATION
               if (!filtred_p3v3_ok || !filtred_hvCup_safe
                       || ((SystemTime - masterLastPacketTime) > TIMEOUT_COMMUNICATION
                       || (SystemTime - acuLastPacketTime) > TIMEOUT_COMMUNICATION)){
                   Current_state = FAIL_SAFE; // Transition to WAIT_FOR_ARM
               }

               else if (!filtred_hvCup_safe && (SystemTime >= TIMEOUT_DISARM_TIMEOUT)) {
                   Current_state = WAIT_FOR_ARM; // Transition to WAIT_FOR_ARM
                   defaultFiltersAndTimers();
               }
               else{
                   Current_state = DISARM; // Transition to WAIT_FOR_ARM
               }
           }
           break;

           case FAIL_SAFE: // 12: Fail Safe / Emergency State
           {
               //Current_state = FAIL_SAFE;
               Current_state = PBIT;
               GPIO_writePin(SW1_2EN, 0);
               GPIO_writePin(GCLK_TO_MCU2, 0);
               GPIO_writePin(TRIG_P, 0);
               GPIO_writePin(TRIG_N, 1);
               defaultFiltersAndTimers();
           }
           break;

           case SEC_DET_ATTEMPT: // 13: Secondary Detection Attempt
           {
               startGclk();
               GPIO_writePin(SW1_2EN, 1);
               GPIO_writePin(TRIG_P, 1);
               GPIO_writePin(TRIG_N, 0);

               if (SystemTime >= TIMEOUT_DET2_TIMEOUT){
                   Current_state = DUD; // Transition to FAIL_SAFE
               }
           }
           break;

           case DUD: // 14: Inoperative or DUD State
           {
               GPIO_writePin(SW1_2EN, 0);
               GPIO_writePin(GCLK_TO_MCU2, 0);
               GPIO_writePin(TRIG_P, 0);
               GPIO_writePin(TRIG_N, 1);
               defaultFiltersAndTimers();
           }
           break;

           default:
           {
               // If an undefined state is encountered, default back to PBIT.
               Current_state = PBIT;
           }
           break;
           } // end switch
    }
}

