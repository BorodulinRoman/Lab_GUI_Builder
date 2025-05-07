#ifndef UART_OPERATION_MASTER_H_
#define UART_OPERATION_MASTER_H_

#include "sci.h"
#include "gpio.h"
#include "globals_and_gpio.h"
#include "common_defines.h"
#include "globals_and_gpio.h"
#include "uart_operation_acu.h"
//#include "uart_operation_master.h"  // To share MSPMsg_t and computeCRC_MSP()


#define UID1_ADDRESS 0x0007114AU
#define UID2_ADDRESS 0x0007114CU

// ACU UART configuration
#define MASTER_DEVICE_PIN_SCIRXDB  226
#define MASTER_DEVICE_PIN_SCITXDB  224
#define MASTER_DEVICE_CFG_SCIRXDB  GPIO_226_SCIC_RX
#define MASTER_DEVICE_CFG_SCITXDB  GPIO_224_SCIC_TX
#define mySCIC_BASE              SCIC_BASE


extern volatile uint8_t rxBufferMaster[RX_MSG_LENGTH];
extern volatile bool newDataReceivedMaster;

// Global ACU message instance (last built packet)
extern MSPMsg_t receivedMsgMaster;

// Global flag to enable ACU transmissions.
extern volatile bool masterEnableTx;
// Global packet counter for ACU transmissions.
extern volatile uint16_t masterPacketCount;

void uartConfigMaster(void);
void uartMsgTxMaster(void);
void uartMsgRxMaster(void);

// Updated CRC function: returns 8-bit value.
// (We share computeCRC_MSP() from the Master module if identical.)
void masterBuildPayload(MSPMsg_t *msg);
void masterDecodePayload(const MSPMsg_t *msg);

bool checkComOkMaster(uint16_t filter_protocol);

#endif /* UART_OPERATION_MASTER_H_ */
