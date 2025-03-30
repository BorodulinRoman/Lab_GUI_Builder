#ifndef ACCELEROMETER_H_
#define ACCELEROMETER_H_

#include <stdint.h>
#include <stdbool.h>
#include "accelerometer.h"
// Initializes SPI and configures the KX134 accelerometer.
void accelerometer_init(void);

// Reads the X, Y, Z axes from the accelerometer and updates
// the global variables aclX, aclY, aclZ.
extern void accelerometer_readXYZ(void);

#endif /* ACCELEROMETER_H_ */
