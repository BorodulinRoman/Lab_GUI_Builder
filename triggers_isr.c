//#include "triggers_isr.h"
//
////
//// cpuTimer0ISR()
////   - Called each time Timer0 overflows (~10 ms).
////   - Toggles GPIO29 instead of GPIO31.
////
//__interrupt void cpuTimer0ISR(void)
//{
//    //
//    // 1) Toggle GPIO29 (updated)
//    //
//    GPIO_togglePin(29);
//
//    //
//    // 2) Clear the timer overflow flag
//    //
//    CPUTimer_clearOverflowFlag(CPUTIMER0_BASE);
//
//    //
//    // 3) Acknowledge PIE interrupt group for Timer0 (usually group 1).
//    //
//    Interrupt_clearACKGroup(INTERRUPT_ACK_GROUP1);
//}
//
////
//// initTimer0Interrupt()
////   - Registers the Timer0 ISR & enables it in the PIE.
////
//void initTimer0Interrupt(void)
//{
//    //
//    // 1) Register the ISR
//    //
//    Interrupt_register(INT_TIMER0, &cpuTimer0ISR);
//
//    //
//    // 2) Enable this interrupt in the PIE
//    //
//    Interrupt_enable(INT_TIMER0);
//}
