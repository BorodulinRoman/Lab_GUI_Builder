#ifndef UART_OPERATION_MASTER_H_
#define UART_OPERATION_MASTER_H_

#include "device.h"
#include "board.h"
#include "driverlib.h"
#include "sci.h"
#include "gpio.h"
#include "globals_and_gpio.h"

// Master UART configuration using SCIC
#define DEVICE_PIN_SCIRXDC 226U
#define DEVICE_PIN_SCITXDC 224U
#define DEVICE_CFG_SCIRXDC GPIO_226_SCIC_RX
#define DEVICE_CFG_SCITXDC GPIO_224_SCIC_TX

// Global Master message instance (last built packet)
extern MSPMsg_t receivedMsgMaster;

// Global packet counter for Master transmissions.
extern volatile uint16_t masterPacketCount;

void uartConfigMaster(void);
void uartMsgTxMaster(void);
void uartMsgRxMaster(void);

void masterBuildPayload(MSPMsg_t *msg);
void masterDecodePayload(const MSPMsg_t *msg);

// Returns true if masterPacketCount is at least filter_protocol, then resets the counter.
bool checkComOkMaster(uint16_t filter_protocol);

#endif /* UART_OPERATION_MASTER_H_ */
