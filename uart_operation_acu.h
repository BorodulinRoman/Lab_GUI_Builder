#ifndef UART_OPERATION_ACU_H_
#define UART_OPERATION_ACU_H_

#include "sci.h"
#include "gpio.h"
#include "globals_and_gpio.h"
#include "common_defines.h"
#include "globals_and_gpio.h"
//#include "uart_operation_master.h"  // To share MSPMsg_t and computeCRC_MSP()


#define UID1_ADDRESS 0x0007114AU
#define UID2_ADDRESS 0x0007114CU

// ACU UART configuration
#define ACU_DEVICE_PIN_SCIRXDB  13
#define ACU_DEVICE_PIN_SCITXDB  12
#define ACU_DEVICE_CFG_SCIRXDB  GPIO_13_SCIB_RX
#define ACU_DEVICE_CFG_SCITXDB  GPIO_12_SCIB_TX
#define mySCI_BASE              SCIB_BASE


extern volatile uint8_t rxBufferACU[RX_MSG_LENGTH];
extern volatile bool newDataReceivedACU;

// Global ACU message instance (last built packet)
extern MSPMsg_t receivedMsgACU;

// Global flag to enable ACU transmissions.
extern volatile bool acuEnableTx;
// Global packet counter for ACU transmissions.
extern volatile uint16_t acuPacketCount;

void handShake(void);
void uartConfigACU(void);
void uartMsgTxACU(void);
void uartMsgRxACU(void);

// Updated CRC function: returns 8-bit value.
// (We share computeCRC_MSP() from the Master module if identical.)
void acuBuildPayload(MSPMsg_t *msg);
void acuDecodePayload(const MSPMsg_t *msg);

bool checkComOkACU(uint16_t filter_protocol);

#endif /* UART_OPERATION_ACU_H_ */
