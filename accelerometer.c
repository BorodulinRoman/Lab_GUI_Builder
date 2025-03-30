#include "accelerometer.h"
#include "globals_and_gpio.h"    // For aclX, aclY, aclZ, and pin definitions
#include "device.h"
#include "driverlib.h"
#include "accelerometer.h"
//=============================================================================
// KX134 Register Addresses (example values; refer to your KX134 datasheet!)
//=============================================================================
#define KX134_REG_WHO_AM_I       0x13
#define KX134_REG_WHO_AM_I_ID    0xCC
#define KX134_REG_CNTL1          0x1B
#define KX134_REG_ODCNTL         0x1D
#define KX134_REG_XOUT_L         0x08

//=============================================================================
// SPI Configuration for TMS320F280015x Example
//   Using SPIA_BASE as an example. Verify pin-muxing is correct for your pins!
//=============================================================================

volatile bool accelerometerAvailable = true;  // Sensor responded = false;
// Helper function to pull CS low
static inline void spiAssertCS(void)
{
    GPIO_writePin(CS_MCU1, 0);  // Active LOW
}

// Helper function to release CS high
static inline void spiDeassertCS(void)
{
    GPIO_writePin(CS_MCU1, 1);  // Inactive
}

//=============================================================================
// Send one byte via SPI, then read one byte back
//=============================================================================
static uint16_t spiTransferByte(uint16_t data)
{
    uint32_t timeout = 10000;  // ערך שיתן מספיק זמן אך לא אינסופי

    // שלח את ה-Data
    while(SPI_getTxFIFOStatus(SPIA_BASE) == SPI_FIFO_TX16 && --timeout);
    if(timeout == 0) return 0xFF;  // יציאה עם שגיאה

    SPI_writeDataBlockingNonFIFO(SPIA_BASE, data);

    // איפוס timeout לקריאה
    timeout = 10000;

    while(SPI_getRxFIFOStatus(SPIA_BASE) == SPI_FIFO_RX0 && --timeout);
    if(timeout == 0) return 0xFF;  // יציאה עם שגיאה

    return SPI_readDataBlockingNonFIFO(SPIA_BASE);
}

//=============================================================================
// Write one byte to a KX134 register
//   reg = register address
//   val = value to write
//=============================================================================
static void kx134_writeRegister(uint8_t reg, uint8_t val)
{
    // KX134 uses [7:0]=RegisterAddress, Write by clearing bit7 (0=Write, 1=Read)
    // Check datasheet for exact SPI format: some require MSB=R/W bit.
    // If R/W bit is bit7, then for write we ensure bit7=0
    uint16_t addressByte = (reg & 0x7F);  // Clear bit7 for write

    spiAssertCS();

    // Send address
    spiTransferByte(addressByte);
    // Send data
    spiTransferByte(val);

    spiDeassertCS();
}

//=============================================================================
// Read one byte from a KX134 register
//=============================================================================
static uint8_t kx134_readRegister(uint8_t reg)
{
    // For read, set bit7=1 in the address. (Check the KX134 datasheet.)
    uint8_t addressByte = (reg & 0x7F) | 0x80;
    uint16_t val;

    spiAssertCS();

    // Send address w/ read bit
    spiTransferByte(addressByte);
    // Receive data
    val = spiTransferByte(0x00);

    spiDeassertCS();

    return (uint8_t)(val & 0x00FF);
}

//=============================================================================
// Setup the SPI module for communication with the KX134
//=============================================================================
static void initSPI(void)
{
    // -------------------------------------------------------------------------
    // 1) Configure GPIO for SPI signals (GPIO0=CS, GPIO1=MISO, GPIO2=MOSI, GPIO3=SCLK).
    // Make sure these pins can indeed be used by SPIA. If the device does not
    // allow hardware routing of SPIA to these pins, you may need to do bit-bang SPI,
    // or pick different pins. For now, we assume the pin mux supports it.
    // -------------------------------------------------------------------------
    // Make CS a GPIO output (manual chip select).
    GPIO_setPadConfig(CS_MCU1, GPIO_PIN_TYPE_STD);
    GPIO_setDirectionMode(CS_MCU1, GPIO_DIR_MODE_OUT);
    spiDeassertCS();  // inactive by default

    // For hardware MISO, MOSI, SCLK (assuming these can be pinned to SPIA):
    GPIO_setPinConfig(GPIO_1_SPIA_SOMI);  // KX134 MISO
    GPIO_setPinConfig(GPIO_2_SPIA_SIMO);  // KX134 MOSI
    GPIO_setPinConfig(GPIO_3_SPIA_CLK);   // KX134 SCLK

    // -------------------------------------------------------------------------
    // 2) Configure the SPI module
    // -------------------------------------------------------------------------
    // Disable SPI to configure
    SPI_disableModule(SPIA_BASE);

    // SPI clock = LSPCLK / prescale. For maximum speed, pick highest rate KX134 can handle.
    // Suppose KX134 can handle several MHz. We'll pick a moderate setting here:
    SPI_setConfig(SPIA_BASE, DEVICE_LSPCLK_FREQ, SPI_PROT_POL0PHA0,
                  SPI_MODE_MASTER, 4000000, 8); // 4MHz, 8-bit

    // Use FIFO for fast transfers
    SPI_enableFIFO(SPIA_BASE);
    SPI_setFIFOInterruptLevel(SPIA_BASE, SPI_FIFO_TX0, SPI_FIFO_RX0);
    SPI_clearInterruptStatus(SPIA_BASE, SPI_INT_TXFF | SPI_INT_RXFF);


    // Enable the SPI module
    SPI_enableModule(SPIA_BASE);
}

//=============================================================================
// Perform basic KX134 initialization: check WHO_AM_I, set up sample rate, etc.
//=============================================================================
void accelerometer_init(void)
{
    // 1) Initialize hardware SPI
    initSPI();

    // 2) Verify device ID
    uint8_t whoami = kx134_readRegister(KX134_REG_WHO_AM_I);
    if (whoami == KX134_REG_WHO_AM_I_ID)
    {
        accelerometerAvailable = true;  // Sensor responded
    }
    else
    {
        accelerometerAvailable = false;
        // Optionally log or set an error flag here
        // e.g. sensorError = SENSOR_ACCELEROMETER_NOT_DETECTED;
        // But we do NOT return from the function.
    }

    // 3) Configure data rate, full-scale, etc.
    //    Even if sensor is not responding, we can attempt the writes if you want.
    kx134_writeRegister(KX134_REG_ODCNTL, 0x0A);
    kx134_writeRegister(KX134_REG_CNTL1, 0xA7);
}

//=============================================================================
// Reads X, Y, Z from the KX134, storing upper 8 bits into aclX, aclY, aclZ
//=============================================================================
void accelerometer_readXYZ(void)
{
    if(!accelerometerAvailable)
    {
        // If sensor not available, do nothing or store dummy values
        aclX = 0;
        aclY = 0;
        aclZ = 0;
        return;
    }

    // Otherwise, read X/Y/Z as normal
    uint8_t xL = kx134_readRegister(KX134_REG_XOUT_L);
    uint8_t xH = kx134_readRegister(KX134_REG_XOUT_L + 1);
    uint8_t yL = kx134_readRegister(KX134_REG_XOUT_L + 2);
    uint8_t yH = kx134_readRegister(KX134_REG_XOUT_L + 3);
    uint8_t zL = kx134_readRegister(KX134_REG_XOUT_L + 4);
    uint8_t zH = kx134_readRegister(KX134_REG_XOUT_L + 5);

    aclX = xH;
    aclY = yH;
    aclZ = zH;
}
