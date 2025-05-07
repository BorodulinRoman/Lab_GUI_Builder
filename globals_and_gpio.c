#include "globals_and_gpio.h"


MSPMsg_t receivedMsgACU;

MSPMsg_t receivedMsgMaster;

// Track the last time (in ms) a valid Master packet was received.
volatile uint32_t masterLastPacketTime = 0;
volatile uint32_t acuLastPacketTime = 0;

// Define the global variables.
volatile int Current_state = 0;
volatile bool newDataReceivedSlave = false;

volatile uint16_t functionTX = IDENTIFY_RFM_ACU;
volatile uint16_t functionRX = 0;

// Define the Master RX buffer (41 bytes for our MSP message) and its index:
volatile uint8_t rxBufferMaster[RX_MSG_LENGTH] = {0};
volatile uint8_t rxBufferACU[RX_MSG_LENGTH] = {0};
volatile uint16_t rxIndexMaster = 0;
volatile uint16_t rxIndexACU = 0;
volatile bool newDataReceivedMaster = false;
volatile bool newDataReceivedACU = false;

// Define the buffers and indices (for Master RX/TX).
volatile uint8_t txBufferMaster[TX_MSG_LENGTH] = {0};
volatile uint16_t txIndexMaster = 0;
volatile uint16_t txLengthMaster = 0;



void initGclkEPWM(void)
{
    // Configure GPIO16 (GDC_TO_MCU2) to EPWM5A (check datasheet for correct pin mapping)
    GPIO_setPinConfig(GPIO_16_EPWM5_A);  // This maps GPIO16 to EPWM5A
    GPIO_setDirectionMode(GCLK_TO_MCU2, GPIO_DIR_MODE_OUT);

    // Disable TBCLK sync for setup
    SysCtl_disablePeripheral(SYSCTL_PERIPH_CLK_TBCLKSYNC);

    // Set the time base clock to system clock
    EPWM_setClockPrescaler(EPWM5_BASE, EPWM_CLOCK_DIVIDER_1, EPWM_HSCLOCK_DIVIDER_1);

    // Set counter mode to Up-Down Count
    EPWM_setTimeBaseCounterMode(EPWM5_BASE, EPWM_COUNTER_MODE_UP_DOWN);

    // Calculate period for 440 kHz
    uint32_t period = (DEVICE_SYSCLK_FREQ / 440000) / 2;  // Up-down count divides by 2
    EPWM_setTimeBasePeriod(EPWM5_BASE, period);

    // Set duty cycle to 50% (up/down mode automatically centers this)
    EPWM_setCounterCompareValue(EPWM5_BASE, EPWM_COUNTER_COMPARE_A, period / 2);

    // Set action qualifier - toggle output at zero and period
    EPWM_setActionQualifierAction(EPWM5_BASE, EPWM_AQ_OUTPUT_A,
                                  EPWM_AQ_OUTPUT_TOGGLE,
                                  EPWM_AQ_OUTPUT_ON_TIMEBASE_ZERO);
    EPWM_setActionQualifierAction(EPWM5_BASE, EPWM_AQ_OUTPUT_A,
                                  EPWM_AQ_OUTPUT_TOGGLE,
                                  EPWM_AQ_OUTPUT_ON_TIMEBASE_PERIOD);

    // Enable TBCLK sync after setup
    SysCtl_enablePeripheral(SYSCTL_PERIPH_CLK_TBCLKSYNC);

}

// Function to set up the GPIOs
void setupGPIOs(void)
{
    // Configure OUT GPIOs
    GPIO_setPinConfig(GPIO_0_GPIO0);  // CS_MCU1
    GPIO_setPinConfig(GPIO_2_GPIO2);  // MOSI_MCU1
    GPIO_setPinConfig(GPIO_3_GPIO3);  // SCLK_MCU1
    GPIO_setPinConfig(GPIO_7_GPIO7);  // SW1_2EN
    GPIO_setPinConfig(GPIO_16_GPIO16); // GDC_TO_MCU2
    GPIO_setPinConfig(GPIO_32_GPIO32); // TRIG_P
    GPIO_setPinConfig(GPIO_33_GPIO33); // TRIG_N

    GPIO_setDirectionMode(CS_MCU1, GPIO_DIR_MODE_OUT);
    GPIO_setDirectionMode(MOSI_MCU1, GPIO_DIR_MODE_OUT);
    GPIO_setDirectionMode(SCLK_MCU1, GPIO_DIR_MODE_OUT);
    GPIO_setDirectionMode(SW1_2EN, GPIO_DIR_MODE_OUT);
    GPIO_setDirectionMode(GCLK_TO_MCU2, GPIO_DIR_MODE_OUT);
    GPIO_setDirectionMode(TRIG_P, GPIO_DIR_MODE_OUT);
    GPIO_setDirectionMode(TRIG_N, GPIO_DIR_MODE_OUT);

    // Set default output levels
    GPIO_writePin(CS_MCU1, 1);
    GPIO_writePin(MOSI_MCU1, 0);
    GPIO_writePin(SCLK_MCU1, 0);
    GPIO_writePin(SW1_2EN, 0);
    GPIO_writePin(GCLK_TO_MCU2, 0);
    GPIO_writePin(TRIG_P, 0);
    GPIO_writePin(TRIG_N, 1);

    // Configure IN GPIOs
    GPIO_setPinConfig(GPIO_1_GPIO1);  // MISO_MCU1
    GPIO_setPinConfig(GPIO_24_GPIO24); // P3V3_GOOD
    GPIO_setPinConfig(GPIO_29_GPIO29); // P5V_SAFETY_GOOD_ISO (if needed)

    GPIO_setDirectionMode(MISO_MCU1, GPIO_DIR_MODE_IN);
    GPIO_setDirectionMode(P3V3_GOOD, GPIO_DIR_MODE_IN);
    GPIO_setDirectionMode(P5V_SAFETY_GOOD_ISO, GPIO_DIR_MODE_IN);

    GPIO_setQualificationMode(MISO_MCU1, GPIO_QUAL_ASYNC);
    GPIO_setQualificationMode(P3V3_GOOD, GPIO_QUAL_ASYNC);
    GPIO_setQualificationMode(P5V_SAFETY_GOOD_ISO, GPIO_QUAL_ASYNC);
}
