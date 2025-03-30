#ifndef FILTERS_H_
#define FILTERS_H_
#include "globals_and_gpio.h"
#include "timers.h"
#include "adc.h"
#include <stdint.h>
#include <stdbool.h>
#include "device.h"  // For GPIO-related function
// Function Prototypes
uint16_t ADC_read(uint32_t adc_channel);
bool adc_filter(uint32_t sample_count, uint32_t adc_channel, uint32_t threshold, bool above);
bool gpio_stability_filter(uint32_t duration_ms, uint8_t threshold_percentage, uint32_t gpio_pin, bool expected_state);
#endif // FILTERS_H_
