#ifndef TRIGGERS_ISR_H
#define TRIGGERS_ISR_H

#include <stdbool.h>
#include "device.h"
#include "driverlib.h"

//
// Sets up the CPU Timer0 ISR in the interrupt controller
//
void initTimer0Interrupt(void);

//
// The ISR function itself, called on CPU Timer0 overflow
//
__interrupt void cpuTimer0ISR(void);

#endif // TRIGGERS_ISR_H
