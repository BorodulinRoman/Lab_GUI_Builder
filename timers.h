#ifndef TIMERS_H
#define TIMERS_H

#include <stdint.h>
#include <stdbool.h>
#include "device.h"
#include "driverlib.h"

// Global variables
extern volatile uint32_t systemTimeCounter; // System time counter in milliseconds
extern volatile bool systemTimeElapsed;     // Flag indicating if the maximum time has elapsed

// System Timer APIs (using Timer2)
// Initializes the system timer (Timer2) with a 1 ms tick.
void initSystemTimer(void);
// Resets the system timer counter and elapsed flag.
void resetSystemTimer(void);
// Returns the current system time in milliseconds.
uint32_t getSystemTime(void);
// Checks if the system time has elapsed (e.g., 60 seconds).
bool hasSystemTimeElapsed(void);

void startGclk(void);
//// Stops 440 kHz clock output on GDC_TO_MCU2 (GPIO16).
void stopGclk(void);

#endif // TIMERS_H
