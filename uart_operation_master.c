/******************************************************************************
 * File:    uart_operation_master.c
 * Device:  TMS320F280015x (or similar)
 *
 * Purpose:
 *   Implements the Master MSP protocol with a 32-byte payload over SCIC.
 *   The message structure is as follows:
 *     Byte 0: '$'
 *     Byte 1: 'X'
 *     Byte 2: type         (for Master TX, '<' indicates a request)
 *     Byte 3: flag         (0)
 *     Bytes 4-5: function  (little-endian)
 *     Bytes 6-7: payloadSize (little-endian, normally 32)
 *     Bytes 8-39: payload  (32 bytes)
 *     Byte 40: CRC8 computed over bytes 2 to 39 using DVB-S2 polynomial (0xD5)
 *
 *   If the function code equals 0x84, an "empty" message is sent (payloadSize = 0).
 *
 *   The receive function decodes an incoming 41-byte MSP message (expected type '>')
 *   and validates its header and CRC.
 *
 * Author: Roman Borodulin (Updated for Master)
 * Created: 20/01/2025 (Updated Protocol)
 *****************************************************************************/

#include "uart_operation_master.h"

// Global packet counter for Master transmissions.
volatile uint16_t masterPacketCount = 0;
volatile uint16_t commMasterCounter = 0;

// Internal message counter for transmitted messages.
static volatile uint16_t msgCounter = 0;

/******************************************************************************
 * SCIC Interrupt Service Routine: RX
 * - Handles RX FIFO events for SCIC.
 *****************************************************************************/
__interrupt void scicRxISR(void)
{
    uint16_t intStatus = SCI_getInterruptStatus(SCIC_BASE);

    if (intStatus & SCI_INT_RXFF)
    {
        // While RX FIFO is not empty, read data
        while (SCI_getRxFIFOStatus(SCIC_BASE) != SCI_FIFO_RX0)
        {
            uint16_t received = SCI_readCharNonBlocking(SCIC_BASE);

            // Store into rxBufferMaster if there is room
            if (rxIndexMaster < RX_MSG_LENGTH)
            {
                rxBufferMaster[rxIndexMaster++] = (uint8_t)received;
            }
            else
            {
                rxIndexMaster = 0;
            }

            // When a full 41-byte message is received, flag and process it
            if (rxIndexMaster == RX_MSG_LENGTH)
            {
                newDataReceivedMaster = true;
                uartMsgRxMaster();
                rxIndexMaster = 0;
            }
        }
    }

    SCI_clearInterruptStatus(SCIC_BASE, SCI_INT_RXFF);
    Interrupt_clearACKGroup(INTERRUPT_ACK_GROUP9);
}

/******************************************************************************
 * SCIC Interrupt Service Routine: TX
 * - Handles TX FIFO events for SCIC.
 *****************************************************************************/
__interrupt void scicTxISR(void)
{
    uint16_t intStatus = SCI_getInterruptStatus(SCIC_BASE);

    if (intStatus & SCI_INT_TXFF)
    {
        uint16_t fifoFree = 16U - SCI_getTxFIFOStatus(SCIC_BASE);

        // Fill the TX FIFO while space exists and data remains to be sent.
        while ((fifoFree > 0) && (txIndexMaster < txLengthMaster))
        {
            SCI_writeCharNonBlocking(SCIC_BASE, txBufferMaster[txIndexMaster++]);
            fifoFree--;
        }

        if (txIndexMaster >= txLengthMaster)
        {
            SCI_disableInterrupt(SCIC_BASE, SCI_INT_TXFF);
            txIndexMaster = 0;
            txLengthMaster = 0;
        }
    }

    SCI_clearInterruptStatus(SCIC_BASE, SCI_INT_TXFF);
    Interrupt_clearACKGroup(INTERRUPT_ACK_GROUP9);
}

/******************************************************************************
 * uartConfigMaster()
 * Configures the SCIC module for UART communication at 115200 baud, 8N1.
 *****************************************************************************/
void uartConfigMaster(void)
{
    // 1. Configure the SCIC RX and TX pin mux.

    GPIO_setPinConfig(DEVICE_CFG_SCIRXDC);
    GPIO_setPinConfig(DEVICE_CFG_SCITXDC);


    GPIO_setAnalogMode(DEVICE_PIN_SCIRXDC, GPIO_ANALOG_DISABLED);
    GPIO_setAnalogMode(DEVICE_PIN_SCITXDC, GPIO_ANALOG_DISABLED);

    // 2. Enable the SCIC peripheral clock.
    //SysCtl_enablePeripheral(SYSCTL_PERIPH_CLK_SCIC);


    // 3. Configure pad settings (standard push-pull).
    GPIO_setPadConfig(DEVICE_PIN_SCIRXDC, GPIO_PIN_TYPE_STD | GPIO_PIN_TYPE_PULLUP);
    GPIO_setPadConfig(DEVICE_PIN_SCITXDC, GPIO_PIN_TYPE_STD | GPIO_PIN_TYPE_PULLUP);

    // 4. Set pin directions: RX as input, TX as output.
//    GPIO_setDirectionMode(DEVICE_PIN_SCIRXDC, GPIO_DIR_MODE_IN);
//    GPIO_setDirectionMode(DEVICE_PIN_SCITXDC, GPIO_DIR_MODE_OUT);
//
//    GPIO_setDirectionMode(DEVICE_PIN_SCIRXDC, GPIO_QUAL_ASYNC);
//    GPIO_setDirectionMode(DEVICE_PIN_SCITXDC, GPIO_QUAL_ASYNC);

    // 5. Set RX qualification to asynchronous.
    GPIO_setQualificationMode(DEVICE_PIN_SCIRXDC, GPIO_QUAL_ASYNC);
    GPIO_setQualificationMode(DEVICE_PIN_SCITXDC, GPIO_QUAL_ASYNC);
    // 6. Perform a software reset of the SCIC module.
    SCI_performSoftwareReset(SCIC_BASE);

    // 7. Configure SCI for 115200 baud, 8 data bits, 1 stop bit, no parity.
    SCI_setConfig(SCIC_BASE,
                  DEVICE_LSPCLK_FREQ,
                  UART_BAUD_RATE_115200,
                  (SCI_CONFIG_WLEN_8 | SCI_CONFIG_STOP_ONE | SCI_CONFIG_PAR_NONE));

    // 8. Enable FIFO, set FIFO interrupt levels, and reset FIFOs.
    SCI_enableFIFO(SCIC_BASE);
    SCI_setFIFOInterruptLevel(SCIC_BASE, SCI_FIFO_TX0, SCI_FIFO_RX1);
    SCI_resetTxFIFO(SCIC_BASE);
    SCI_resetRxFIFO(SCIC_BASE);

    // 9. Clear any pending interrupt status and enable the TX and RX interrupts.
    SCI_clearInterruptStatus(SCIC_BASE, SCI_INT_TXFF | SCI_INT_RXFF);
    SCI_enableInterrupt(SCIC_BASE, SCI_INT_RXFF | SCI_INT_TXFF);

    // 10. Register the ISR functions for SCIC.
    Interrupt_register(INT_SCIC_RX, scicRxISR);
    Interrupt_register(INT_SCIC_TX, scicTxISR);

    // 11. Enable the SCIC interrupts in the interrupt controller.
    Interrupt_enable(INT_SCIC_RX);
    Interrupt_enable(INT_SCIC_TX);

    // 12. Finally, enable the SCIC module.
    SCI_enableModule(SCIC_BASE);

    // 13. Enable global CPU interrupts.
    EINT;
    ERTM;
}

/******************************************************************************
 * uartMsgTxMaster()
 * Builds the MSP message (41 bytes) for Master and triggers transmission.
 *****************************************************************************/
void uartMsgTxMaster(void)
{
    MSPMsg_t transmitMsgMaster;
    txLengthMaster = (receivedMsgACU.payloadSize + 9);

    memcpy(&transmitMsgMaster, &receivedMsgACU, sizeof(MSPMsg_t));
    if (transmitMsgMaster.payloadSize > 0)
    {

        masterBuildPayload(&transmitMsgMaster);
    }
    transmitMsgMaster.crc = 0;
    // Compute CRC over bytes 2 to 39.
    transmitMsgMaster.crc = computeCRC_MSP(&transmitMsgMaster);

    // Copy the message (header, payload, etc.) into the TX buffer.
    uint8_t j;
    for (j = 0; j < (transmitMsgMaster.payloadSize + 8); j++)
    {
        txBufferMaster[j] = ((const uint8_t *)&transmitMsgMaster)[j];
    }
    txBufferMaster[transmitMsgMaster.payloadSize + 8] = transmitMsgMaster.crc;
    // Clear any pending TX interrupt status and enable TX interrupt.
    SCI_clearInterruptStatus(SCIC_BASE, SCI_INT_TXFF);
    SCI_enableInterrupt(SCIC_BASE, SCI_INT_TXFF);
}

/******************************************************************************
 * uartMsgRxMaster()
 * Receives and decodes a 41-byte MSP message for Master.
 *****************************************************************************/
void uartMsgRxMaster(void)
{
    if (newDataReceivedMaster)
    {
        uint8_t i;
        // Parse the message header.
        receivedMsgMaster.start = rxBufferMaster[0];
        receivedMsgMaster.header = rxBufferMaster[1];
        receivedMsgMaster.type = rxBufferMaster[2];
        receivedMsgMaster.flag = rxBufferMaster[3];
        receivedMsgMaster.function_msb = rxBufferMaster[4];
        receivedMsgMaster.function_lsb = rxBufferMaster[5];
        receivedMsgMaster.payloadSize = (uint16_t)rxBufferMaster[6] | ((uint16_t)rxBufferMaster[7] << 8);

        // Limit payload size if necessary.
        if (receivedMsgMaster.payloadSize > 30)
            receivedMsgMaster.payloadSize = 30;

        // Copy the payload.
        for (i = 0; i < receivedMsgMaster.payloadSize; i++)
        {
            receivedMsgMaster.payload[i] = rxBufferMaster[8 + i];
        }

        // Validate header and type (Master expects type '>' for responses)
        if (receivedMsgMaster.start == MSP_START_CHAR &&
            receivedMsgMaster.header == MSP_HEADER_CHAR &&
            receivedMsgMaster.type == MSP_TYPE_RECEIVE)
        {
            // Validate CRC.
            receivedMsgMaster.crc = rxBufferMaster[receivedMsgMaster.payloadSize + 8];
            uint8_t computed_crc = computeCRC_MSP(&receivedMsgMaster);
            if ((computed_crc & 0x00FF) == receivedMsgMaster.crc)
            {
                masterPacketCount++;
                masterLastPacketTime = getSystemTime();
                masterDecodePayload(&receivedMsgMaster);
                // Successfully decoded the message.
            }
            else
            {
                // Handle CRC error as needed.
            }
        }
        else
        {
            // Handle invalid header/type if needed.
        }
        rxIndexMaster = 0;
        newDataReceivedMaster = false;
    }
}

/******************************************************************************
 * masterBuildPayload()
 * Builds the payload for the Master message.
 * If the function code equals 0x84, an empty payload is built.
 *****************************************************************************/
void masterBuildPayload(MSPMsg_t *msg)
{
    if (msg->function_msb != (uint8_t)((IDENTIFY_RFM_ACU >> 8) & 0xFF) &&
            msg->function_lsb != (uint8_t)(IDENTIFY_RFM_ACU & 0xFF))
    {
        // Update specific payload bytes as needed.
        msg->payload[22] = Current_state;
        msg->payload[24] = (commMasterCounter >> 8) & 0xFF;
        msg->payload[25] = commMasterCounter & 0xFF;
    }

    commMasterCounter++;
}

/******************************************************************************
 * masterDecodePayload()
 * Decodes the payload from a received Master message.
 *****************************************************************************/
void masterDecodePayload(const MSPMsg_t *msg)
{
    if (msg->payloadSize == 0)
    {
        // Empty payload: handle accordingly.
    }
    else
    {
        uint8_t i;
        // Example: iterate through the payload bytes and process them.
        for (i = 0; i < msg->payloadSize; i++)
        {
            // Process each byte as required.
            // For example: processMasterData(msg->payload[i]);
        }
    }
}

/******************************************************************************
 * checkComOkMaster()
 * Returns true if masterPacketCount is at least filter_protocol, then resets the counter.
 *****************************************************************************/
bool checkComOkMaster(uint16_t filter_protocol)
{
    if (masterPacketCount >= filter_protocol)
    {
        masterPacketCount = 0;
        return true;
    }
    return false;
}
