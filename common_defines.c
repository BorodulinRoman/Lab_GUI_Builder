
#include "common_defines.h"



// -----------------------------------------------------------------------------
// Static CRC8 Calculation using DVB-S2 polynomial 0xD5 (internal linkage)
// -----------------------------------------------------------------------------
static uint8_t crc8_dvb_s1(uint8_t crc, unsigned char a)
{
    crc ^= a;
    int ii;  // Declare loop index variable outside loop header.
    for (ii = 0; ii < 8; ii++)
    {
        if (crc & 0x80)
        {
            crc = (crc << 1) ^ 0xD5;
        }
        else
        {
            crc = crc << 1;
        }
    }
    return crc;
}

// Computes the CRC8 over bytes 2 through 39 (38 bytes) of the message.
uint8_t computeCRC_MSP(const MSPMsg_t *msg)
{
    uint8_t crc = 0;
    uint16_t i;
    crc = crc8_dvb_s1(crc, msg->flag);

    // Process function (2 bytes, little-endian split)
    crc = crc8_dvb_s1(crc, msg->function_msb);
    crc = crc8_dvb_s1(crc, msg->function_lsb);

    // Process payloadSize (2 bytes, little-endian split)
    crc = crc8_dvb_s1(crc, (uint8_t)((msg->payloadSize >> 8) & 0xFF)); // MSB
    crc = crc8_dvb_s1(crc, (uint8_t)(msg->payloadSize & 0xFF));      // LSB


    // Process payload (32 bytes)
    for (i = 0; i < msg->payloadSize; i++)
    {
        crc = crc8_dvb_s1(crc, msg->payload[i]);
    }

    return crc & 0x00FF;  // Final 8-bit CRC
}
