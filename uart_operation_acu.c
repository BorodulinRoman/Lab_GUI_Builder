/******************************************************************************
 * File:    uart_operation_acu.c
 * Device:  TMS320F280015x (or similar)
 *
 * Purpose:
 *   Implements the ACU MSP protocol using a 41-byte message with a 32-byte payload.
 *   The message structure is as follows:
 *     Byte 0: TX_MSG_HEADER_BYTE0_ACU (0xE5)
 *     Byte 1: TX_MSG_HEADER_BYTE1_ACU (0xED)
 *     Byte 2: type         (for ACU TX, use MSP_TYPE_RECEIVE, i.e. '>')
 *     Byte 3: flag         (0)
 *     Bytes 4-5: function  (little-endian)
 *     Bytes 6-7: payloadSize (little-endian; normally 32)
 *     Bytes 8-39: payload  (32 bytes)
 *     Byte 40: CRC8 computed over bytes 2 to 39 using DVB-S2 polynomial (0xD5)
 *
 *   For function code 0x84, an "empty" message is sent (payloadSize = 0).
 *
 * Author: Roman Borodulin (Updated for ACU)
 * Created: 20/01/2025 (Updated Protocol)
 *****************************************************************************/

// Forward declarations for ACU ISR functions.
__interrupt void scibRxISR(void);
__interrupt void scibTxISR(void);

#include "uart_operation_acu.h"
#include "globals_and_gpio.h"



// Global ACU message instance.
//MSPMsg_t receivedMsgACU;

// Global flag to enable ACU transmission.
volatile bool acuEnableTx = false;
// Global packet counter for ACU transmissions.
volatile uint16_t acuPacketCount = 0;

// ACU RX decoders
volatile uint16_t acuHeader1 = 0;
volatile uint16_t acuHeader2 = 0;
volatile uint8_t error_type = 0 ;
volatile uint16_t rfmLogic1ID = 0;
volatile uint16_t rfmLogic2ID = 0;
volatile uint16_t acuLogic1ID = 0;
volatile uint16_t acuLogic2ID = 0;
volatile uint8_t  messageRFM = 0;
volatile uint8_t  acuStatusAndImpact = 0;
volatile uint8_t  rfmLogicState = 0;  // updated from rfmLogicSate
volatile uint8_t  acuCommand = 0;
volatile uint16_t acuLastReceivedCounter = 0;
volatile uint16_t commCounter = 0;

// ACU TX decoders (use unique names to avoid conflict with RX decoders)

volatile uint16_t armingHeader1 = 0;
volatile uint16_t armingHeader2 = 0;

volatile uint16_t mc1Logic1ID = 0;
volatile uint16_t mc1Logic2ID = 0;
volatile uint16_t mc2Logic1ID = 0;
volatile uint16_t mc2Logic2ID = 0;
volatile uint8_t  mcLogicState = 0;   // updated from mcLogicSate
volatile uint16_t mcLastReceivedCounter = 0;
volatile uint16_t commCounterTX = 0;
volatile uint8_t  capacitorVoltage = 0;
volatile uint8_t  fpg1UniqueArmComm = 0;
volatile uint8_t  fpg2UniqueArmComm = 0;
volatile uint8_t  aclX = 0;
volatile uint8_t  aclY = 0;
volatile uint8_t  aclZ = 0;
volatile bool   handShakeOK = false;


// Static TX buffers and counters for ACU.
static volatile uint8_t txBufferACU[TX_MSG_LENGTH];
static volatile uint16_t txIndexACU = 0;
static volatile uint16_t txLengthACU = 0;

// Message counter for ACU transmissions.
static volatile uint16_t acuMsgCounter = 0;

void readUID(uint32_t addr)
{
    uint32_t uid = HWREG(addr);
    mc1Logic1ID = (uint16_t)((uid >> 16) & 0xFFFF);
    mc1Logic2ID = (uint16_t)(uid & 0xFFFF);
}


void handShake(void)
{
    if (acuStatusAndImpact == HAND_SHAKKE1) {
        messageRFM = HAND_SHAKKE1;
    }
    else if (acuStatusAndImpact == HAND_SHAKKE2 && messageRFM == HAND_SHAKKE1) {
        messageRFM = HAND_SHAKKE2;
    }
    else if (acuStatusAndImpact == HAND_SHAKKE3 && messageRFM == HAND_SHAKKE2) {
        handShakeOK = true;
    }
}

// -----------------------------------------------------------------------------
// uartConfigACU()
// Configures SCIB for UART communication at 115200 baud, 8N1, FIFO mode.
// -----------------------------------------------------------------------------
void uartConfigACU(void)
{

    GPIO_setAnalogMode(ACU_DEVICE_PIN_SCIRXDB, GPIO_ANALOG_DISABLED);
    GPIO_setAnalogMode(ACU_DEVICE_PIN_SCITXDB, GPIO_ANALOG_DISABLED);

    // 1) Configure GPIOs for SCIB.
    GPIO_setPinConfig(ACU_DEVICE_CFG_SCIRXDB);
    GPIO_setPinConfig(ACU_DEVICE_CFG_SCITXDB);

    GPIO_setPadConfig(ACU_DEVICE_PIN_SCIRXDB, GPIO_PIN_TYPE_STD | GPIO_PIN_TYPE_PULLUP);
    GPIO_setPadConfig(ACU_DEVICE_PIN_SCITXDB, GPIO_PIN_TYPE_STD | GPIO_PIN_TYPE_PULLUP);
    GPIO_setQualificationMode(ACU_DEVICE_PIN_SCIRXDB, GPIO_QUAL_ASYNC);

    // 2) Reset/initialize SCIB.
    SCI_performSoftwareReset(mySCI_BASE);

    // 3) Set configuration: 115200 baud, 8N1.
    SCI_setConfig(mySCI_BASE,
                  DEVICE_LSPCLK_FREQ,
                  UART_BAUD_RATE_115200,
                  (SCI_CONFIG_WLEN_8 | SCI_CONFIG_STOP_ONE | SCI_CONFIG_PAR_NONE));

    // 4) Enable FIFO and set interrupt trigger levels.
    SCI_enableFIFO(mySCI_BASE);
    SCI_setFIFOInterruptLevel(mySCI_BASE, SCI_FIFO_TX0, SCI_FIFO_RX1);
    SCI_resetTxFIFO(mySCI_BASE);
    SCI_resetRxFIFO(mySCI_BASE);

    // 5) Clear any pending status.
    SCI_clearInterruptStatus(mySCI_BASE, SCI_INT_TXFF | SCI_INT_RXFF);

    // 6) Enable SCI interrupt sources.
    SCI_enableInterrupt(mySCI_BASE, SCI_INT_RXFF | SCI_INT_TXFF);

    // 7) Register ISR handlers.
    Interrupt_register(INT_SCIB_RX, &scibRxISR);
    Interrupt_register(INT_SCIB_TX, &scibTxISR);

    // 8) Enable interrupts in PIE.
    Interrupt_enable(INT_SCIB_RX);
    Interrupt_enable(INT_SCIB_TX);

    // 9) Enable the SCI module.
    SCI_enableModule(mySCI_BASE);

}

// Builds the payload for the ACU message.
// If the function code is 0x84, it produces an "empty" message (payloadSize = 0).
void acuBuildPayload(MSPMsg_t *msg)
{
    uint8_t i;  // Declare loop index variable outside the loop header.
    functionTX = ACU_ARM_COMMAND;

    //for identification message
    if (Current_state == IDNTIF_RFM_FLIGHT_MODULE) {
        functionTX = IDENTIFY_RFM_ACU;
        msg->payloadSize = 0;
        readUID(UID1_ADDRESS);
        mc2Logic2ID = (receivedMsgMaster.payload[6] << 8) | receivedMsgMaster.payload[6];




    }
    else{
        //for handshake message
        if(Current_state == ARMING_HAND_SHAKE){
            handShake();
            msg->payload[0] = (ACU_HEADER_TX >> 8) & 0xFF; // index 0
            msg->payload[1] = ACU_HEADER_TX & 0xFF;        // index 1
            msg->payload[2] = (ACU_HEADER_TX >> 8) & 0xFF;
            msg->payload[3] = ACU_HEADER_TX & 0xFF;
            msg->payload[12] = messageRFM;

        }
        //for statues message
        else
        {
            msg->payload[0] = (ACU_HEADER_TX >> 8) & 0xFF; // index 0
            msg->payload[1] = ACU_HEADER_TX & 0xFF;        // index 1
            msg->payload[2] = (ACU_HEADER_TX >> 8) & 0xFF;
            msg->payload[3] = ACU_HEADER_TX & 0xFF;
            msg->payload[12] = acuStatusAndImpact;
        }

        msg->payloadSize = 32;
        msg->payload[4] = (mc1Logic1ID >> 8) & 0xFF;
        msg->payload[5] = mc1Logic1ID & 0xFF;
        msg->payload[6] = (mc2Logic2ID >> 8) & 0xFF;
        msg->payload[7] = mc2Logic2ID & 0xFF;

        msg->payload[8] = (acuLogic1ID >> 8) & 0xFF;
        msg->payload[9] = acuLogic1ID & 0xFF;
        msg->payload[10] = (acuLogic2ID >> 8) & 0xFF;
        msg->payload[11] = acuLogic2ID & 0xFF;

        msg->payload[13] = Current_state;
        msg->payload[14] = (mcLastReceivedCounter >> 8) & 0xFF;
        msg->payload[15] = mcLastReceivedCounter & 0xFF;
        msg->payload[16] = (commCounter >> 8) & 0xFF;
        msg->payload[17] = commCounter & 0xFF;
        msg->payload[18] = (uint8_t)(capacitorVoltage & 0xFF);
        msg->payload[19] = (uint8_t)(aclX & 0xFF);
        msg->payload[20] = (uint8_t)(aclY & 0xFF);
        msg->payload[21] = (uint8_t)(aclZ & 0xFF);

        msg->payloadSize = 32;
        for (i = 21; i < msg->payloadSize; i++)
        {
            msg->payload[i] = 0;  // Sample data.
        }
    }
    commCounter++;
}


// Decodes the payload from a received ACU message.
// Replace the processing code below with your application-specific decoding.
void acuDecodePayload(const MSPMsg_t *msg)
{
    if (msg->payloadSize == 0)
    {
        // Empty payload: nothing to process.
    }
    else if (Current_state == ARMING_HAND_SHAKE){

    }
    else
    {
        acuHeader1 =         (msg->payload[1] << 8) | msg->payload[0];
        acuHeader2 =         (msg->payload[3] << 8) | msg->payload[2];
        rfmLogic1ID =        (msg->payload[5] << 8) | msg->payload[4];
        rfmLogic2ID =        (msg->payload[7] << 8) | msg->payload[6];
        acuLogic1ID =        (msg->payload[9] << 8) | msg->payload[8];
        acuLogic2ID =        (msg->payload[11] << 8) | msg->payload[10];
        acuStatusAndImpact =  msg->payload[12];
        rfmLogicState =      msg->payload[13];
        acuLastReceivedCounter = (msg->payload[14] << 8) | msg->payload[15];
        mcLastReceivedCounter  = (msg->payload[16] << 8) | msg->payload[17];
        fpg1UniqueArmComm =  msg->payload[18];
        fpg2UniqueArmComm =  msg->payload[19];
        //20 spare1
        //21 spare2
        //22 l1State
        //23 l2State
        //24-25 l1Counter
        //26-27 l2Counter
        //28-29 spare3
        //30-31 spare4
    }
}

// -----------------------------------------------------------------------------
// uartMsgTxACU()
// Builds the MSP message (41 bytes) for ACU and triggers transmission.
// -----------------------------------------------------------------------------
void uartMsgTxACU(void)
{
    if (!acuEnableTx)
    {
        return;
    }
    MSPMsg_t msg;

    // Build the MSP message.
    msg.start = MSP_START_CHAR;
    msg.header = MSP_HEADER_CHAR;
    msg.type = MSP_TYPE_REQUEST;
    msg.flag = 0;

    acuBuildPayload(&msg);
    msg.empty = 0;
    msg.function_msb = (uint8_t)((functionTX >> 8) & 0xFF);
    msg.function_lsb = (uint8_t)(functionTX & 0xFF);



    uint8_t j;
    for (j = 0; j < (msg.payloadSize + 8); j++)
    {
        txBufferACU[j] = ((const uint8_t *)&msg)[j];
    }


    msg.crc = computeCRC_MSP(&msg);

    txBufferACU[msg.payloadSize + 8] = msg.crc;
    txLengthACU = msg.payloadSize + 9;

    SCI_clearInterruptStatus(mySCI_BASE, SCI_INT_TXFF);
    SCI_enableInterrupt(mySCI_BASE, SCI_INT_TXFF);
}

// -----------------------------------------------------------------------------
// uartMsgRxACU()
// Receives and decodes a 41-byte MSP message for ACU.
// -----------------------------------------------------------------------------
void uartMsgRxACU(void)
{
    if(newDataReceivedACU)
    {
        // 1) Parse header fields
        receivedMsgACU.start         = rxBufferACU[0];
        receivedMsgACU.header        = rxBufferACU[1];
        receivedMsgACU.type          = rxBufferACU[2];
        receivedMsgACU.flag          = rxBufferACU[3];
        receivedMsgACU.function_msb  = rxBufferACU[4];
        receivedMsgACU.function_lsb  = rxBufferACU[5];

        // 2) Parse payload size (two bytes, little-endian)
        receivedMsgACU.payloadSize = (uint16_t)rxBufferACU[6];
        receivedMsgMaster.empty = (uint16_t)rxBufferMaster[7];
        uint16_t i;
        for(i = 0; i < receivedMsgACU.payloadSize; i++)
        {
            receivedMsgACU.payload[i] = rxBufferACU[8 + i];
        }

        // 5) Copy the CRC (assuming after payload, i.e. [payloadSize + 8])
        receivedMsgACU.crc = rxBufferACU[receivedMsgACU.payloadSize + 8];

        // 6) Validate the header & type
        if(  (receivedMsgACU.start  == MSP_START_CHAR) && (receivedMsgACU.header == MSP_HEADER_CHAR))
        {

            if(  (Current_state == IDNTIF_RFM_FLIGHT_MODULE) && (acuLogic1ID == 0) && (acuLogic2ID == 0) )
            {
                acuLogic1ID = (receivedMsgACU.payload[9]  << 8) | receivedMsgACU.payload[8];
                acuLogic2ID = (receivedMsgACU.payload[11] << 8) | receivedMsgACU.payload[10];
            }
            // Case B: Normal reception: check if IDs match what we expect
            else if( (acuLogic1ID == ( (receivedMsgACU.payload[9]  << 8) | receivedMsgACU.payload[8] )) &&
                     (acuLogic2ID == ( (receivedMsgACU.payload[11] << 8) | receivedMsgACU.payload[10])) )
            {
                // Compute CRC and compare
                uint8_t computed_crc = computeCRC_MSP(&receivedMsgACU);

                if((computed_crc & 0xFF) == receivedMsgACU.crc)
                {
                    acuPacketCount++;
                    acuLastPacketTime = getSystemTime();
                    acuDecodePayload(&receivedMsgACU);
                    error_type = 0;  // ok
                }
                else
                {
                    error_type = 1;  // CRC error
                }
            }
            else
            {
                error_type = 2;  // Packet doesn't match the expected IDs
            }
        }
        else
        {
            error_type = 3; // Not a valid MSP header/type
        }

        // Clear the "new data" flag

    }
    newDataReceivedACU = false;
}



// -----------------------------------------------------------------------------
// checkComOkACU()
// Returns true if the number of transmitted ACU packets is at least filter_protocol,
// then resets the counter.
// -----------------------------------------------------------------------------
bool checkComOkACU(uint16_t filter_protocol)
{
    if (acuPacketCount >= filter_protocol)
    {
        acuPacketCount = 0;
        return true;
    }
    return false;
}

// -----------------------------------------------------------------------------
// ACU ISR Implementations
// -----------------------------------------------------------------------------
__interrupt void scibRxISR(void)
{
    uint16_t intStatus = SCI_getInterruptStatus(mySCI_BASE);

    if (intStatus & SCI_INT_RXFF)
    {

        static volatile uint16_t rxIndexACULocal = 0;
        while (SCI_getRxFIFOStatus(mySCI_BASE) != SCI_FIFO_RX0)
        {
            uint8_t  received = (uint8_t) SCI_readCharNonBlocking(mySCI_BASE);
            rxBufferACU[rxIndexACULocal++] = (uint8_t)received;

            switch(rxIndexACULocal){
                case IDENT_TX_MSG_LENGTH:
                    if(rxBufferACU[0] != MSP_START_CHAR || rxBufferACU[1] != MSP_HEADER_CHAR || rxBufferACU[2] != MSP_TYPE_RECEIVE){
                        rxIndexACULocal = 0;
                    }
                    else if( rxBufferACU[6] == 0){
                        uartMsgRxACU();
                        newDataReceivedACU = true;
                        rxIndexACULocal = 0;
                    }
                    break;
                case RX_MSG_LENGTH:
                    if( rxBufferACU[6] == 32){
                        uartMsgRxACU();
                        newDataReceivedACU = true;
                        rxIndexACULocal = 0;
                  }
                  break;

                default:
                    if (rxIndexACULocal > 41){
                        rxIndexACULocal = 0;
                    }
                    break;
            }
        }
    }

    SCI_clearInterruptStatus(mySCI_BASE, SCI_INT_RXFF);
    Interrupt_clearACKGroup(INTERRUPT_ACK_GROUP9);
}


__interrupt void scibTxISR(void)
{
    uint16_t intStatus = SCI_getInterruptStatus(mySCI_BASE);

    if (intStatus & SCI_INT_TXFF)
    {
        uint16_t fifoFree = 16U - SCI_getTxFIFOStatus(mySCI_BASE);
        while ((fifoFree > 0) && (txIndexACU < txLengthACU))
        {
            SCI_writeCharNonBlocking(mySCI_BASE, txBufferACU[txIndexACU++]);
            fifoFree--;
        }
        if (txIndexACU >= txLengthACU)
        {
            SCI_disableInterrupt(mySCI_BASE, SCI_INT_TXFF);
            txIndexACU = 0;
            txLengthACU = 0;
        }
    }

    SCI_clearInterruptStatus(mySCI_BASE, SCI_INT_TXFF);
    Interrupt_clearACKGroup(INTERRUPT_ACK_GROUP9);
}
