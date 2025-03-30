#ifndef GLOBALS_AND_GPIO_H
#define GLOBALS_AND_GPIO_H


#include "timers.h"
#include "device.h"
#include "driverlib.h"
#include "common_defines.h"

// OUT GPIO Configurations
#define CS_MCU1               0U // ACCELEROMETER KX134ACR-LBZE2
#define MOSI_MCU1             2U // ACCELEROMETER KX134ACR-LBZE2
#define SCLK_MCU1             3U // ACCELEROMETER KX134ACR-LBZE2
#define SW1_2EN               7U
#define GCLK_TO_MCU2          16U
#define TRIG_P                32U
#define TRIG_N                33U

//
//#define TP33                227U
//#define TP32                230U
//#define TP31                28U
//#define TP30                20U
//#define GPIO01_MC2          18U
//#define GPIO02_MC2          19U
//#define GPIO03_MC2          44U


// IN GPIO Configurations
#define MISO_MCU1             1U // ACCELEROMETER KX134ACR-LBZE2
#define P3V3_GOOD             24U
#define P5V_SAFETY_GOOD_ISO   29U
#define HV_CUP_ADC_CHANNEL    9U

#define SAFETY_CUP_VOLT       1070
#define ARMED_CUP_VOLT        2040
#define FILTER_GPIO           10U   // Number of samples to take
#define FILTER_ACCURACY       70   // Require at least 70% matching
#define FILTER_PROTOCOL       1U


#define ACU_DET_COMMAND       0xE4A2
// Global Variables
extern volatile int Current_state;       // Tracks the current state in the state machine
extern volatile bool newDataReceivedMaster;
extern volatile bool newDataReceivedSlave;
extern volatile uint32_t SystemTime;
// Declare Master RX/ TX buffer variables to be shared with the Master module:
extern volatile uint8_t rxBufferMaster[RX_MSG_LENGTH];   // Our MSP message is 41 bytes
extern volatile uint16_t rxIndexMaster;
extern volatile uint8_t txBufferMaster[TX_MSG_LENGTH];     // TX buffer for a 41-byte packet
extern volatile uint16_t txIndexMaster;
extern volatile uint16_t txLengthMaster;

extern volatile uint32_t masterLastPacketTime;
extern volatile uint32_t acuLastPacketTime;

extern MSPMsg_t receivedMsgACU;
extern MSPMsg_t receivedMsgMaster;


#define TIMER_PERIOD_US                             10000.0f
#define WAKE_UP                                     20
#define TIMEOUT_PBIT                                100
#define TIMEOUT_ARM_DELEY                           60000
#define TIMEOUT_ARM_READY_FOR_SAFETY_PIN            15000
#define TIMEOUT_COMMUNICATION                       15000
#define TIMEOUT_ARM_HANDSHAKE                       15000
#define TIMEOUT_ARMING                              2000
#define TIMEOUT_DET1_TIMEOUT                        2
#define TIMEOUT_DET2_TIMEOUT                        200
#define TIMEOUT_ARMED_NO_ACU_COMMUNICATION          15000
#define TIMEOUT_DISARM                              30000
#define TIMEOUT_DISARM_NO_ACU_COMMUNICATION         15000
#define TIMEOUT_DISARM_TIMEOUT                      15000



void initGclkEPWM(void);
// Function Prototypes
void setupGPIOs(void);

#endif // GLOBALS_AND_GPIO_H
