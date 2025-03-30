#ifndef COMMON_DEFINES_H_
#define COMMON_DEFINES_H_

#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include "device.h"
#include "driverlib.h"

#define RX_MSG_LENGTH 41
#define TX_MSG_LENGTH 41
#define SCI_FIFO_LEVEL_EMPTY  SCI_FIFO_RX0
#define UART_BAUD_RATE_115200     115200

// Define the states
#define PBIT                        1
#define IDNTIF_RFM_FLIGHT_MODULE    2
#define IDNTIF_RFM_ACU              3
#define READY_FOR_SAFETY_PIN        4
#define ARM_DELEY                   5
#define WAIT_FOR_ARM                6
#define ARMING_HAND_SHAKE           7
#define ARMING                      8
#define ARMED                       9
#define DET                         10
#define DISARM                      11
#define FAIL_SAFE                   12
#define SEC_DET_ATTEMPT             13
#define DUD                         14


// ACU rx decoders
extern volatile uint16_t acuHeader1;
extern volatile uint16_t acuHeader2;
extern volatile uint8_t error_type;
extern volatile uint16_t rfmLogic1ID;
extern volatile uint16_t rfmLogic2ID;
extern volatile uint16_t acuLogic1ID;
extern volatile uint16_t acuLogic2ID;
extern volatile uint8_t  messageRFM;
extern volatile uint8_t  acuStatusAndImpact;
extern volatile uint8_t  rfmLogicSate;
extern volatile uint8_t  acuCommand;
extern volatile uint16_t acuLastReceivedCounter;
extern volatile uint16_t commCounter;

// ACU TX decoders (use different names if these should be separate variables)

extern volatile uint16_t armingHeader1;
extern volatile uint16_t armingHeader2;

extern volatile uint16_t mc1Logic1ID;
extern volatile uint16_t mc2Logic2ID;
extern volatile uint16_t acuLogic1ID;
extern volatile uint16_t acuLogic2ID;

extern volatile uint8_t  mcLogicSate;
extern volatile uint16_t mcLastReceivedCounter;
extern volatile uint16_t commCounterTX;
extern volatile uint8_t  capacitorVoltage;
extern volatile uint8_t  fpg1UniqueArmComm;
extern volatile uint8_t  fpg2UniqueArmComm;
extern volatile uint8_t  aclX;
extern volatile uint8_t  aclY;
extern volatile uint8_t  aclZ;
extern volatile bool   handShakeOK;

extern volatile uint16_t functionTX;
extern volatile uint16_t functionRX;


// MSP Message parameters
#define MSP_START_CHAR         0x24
#define MSP_HEADER_CHAR        0x58
#define MSP_TYPE_REQUEST       0x3C
#define MSP_TYPE_RECEIVE       0x3E
#define MSP_DEFAULT_FLAG       0
#define MSP_PAYLOAD_SIZE       128
#define ACU_HEADER_TX          0xAAAA
#define ACU_ARMING_HEADER_TX   0xC2A0

#define HAND_SHAKKE1           0x33
#define HAND_SHAKKE2           0xAA
#define HAND_SHAKKE3           0xCC
// FUNCTIONS and state machine definitions remain unchanged
#define IDENTIFY_RFM_ACU                            0x0084
#define ACU_ARM_COMMAND                             0x9050

// Total packet size: 1 + 1 + 1 + 1 + 2 + 2 + 32 + 1 = 41 bytes.
struct MSPMsg_t {
    uint8_t start;         // Must be '$'
    uint8_t header;        // Must be 'X'
    uint8_t type;          // e.g. '<', '>', or '!'
    uint8_t flag;          // Usually 0
    uint8_t function_msb;     // Function code (little-endian)
    uint8_t function_lsb;     // Function code (little-endian)
    uint16_t payloadSize;  // Should be MSP_PAYLOAD_SIZE (32)
    uint8_t payload[MSP_PAYLOAD_SIZE]; // Payload data
    uint8_t crc;           // 8-bit CRC computed over bytes 0..37 -> crc is 38
};

typedef struct MSPMsg_t MSPMsg_t;

// Computes the CRC8 (using DVB-S2 polynomial 0xD5) over a given data array.
static uint8_t crc8_dvb_s1(uint8_t crc, unsigned char a);
uint8_t computeCRC_MSP(const MSPMsg_t *msg);

#endif /* COMMON_DEFINES_H_ */
