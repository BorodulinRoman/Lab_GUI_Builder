#include "filters.h"
#include "common_defines.h"

uint16_t ADC_read(uint32_t adc_channel)
{
    // Configure SOC0 on ADC module A for the given channel.
    // Use ADC_TRIGGER_SW_ONLY to trigger via software.
    // Here, we use a sample window of 10 cycles (adjust as needed).
    ADC_setupSOC(ADCA_BASE, ADC_SOC_NUMBER0, ADC_TRIGGER_SW_ONLY, (ADC_Channel)adc_channel, 10);

    // Force a conversion on SOC0.
    ADC_forceSOC(ADCA_BASE, ADC_SOC_NUMBER0);

    // Wait until the ADC conversion is complete.
    // ADC_isBusy returns true if the ADC is still converting.
    while (ADC_isBusy(ADCA_BASE))
    {
        ; // Busy wait
    }
    capacitorVoltage = ADC_readResult(ADCARESULT_BASE, ADC_SOC_NUMBER0);
    // Read and return the conversion result from ADC module A.
    return capacitorVoltage;
}
// New ADC filter function.
// This function takes a fixed number of samples from an ADC channel and returns true
// if the percentage of samples that meet the condition (>= or <= threshold)
// is at least the required accuracy defined by FILTER_ACCURACY.
bool adc_filter(uint32_t sample_count, uint32_t adc_channel, uint32_t threshold, bool above)
{
    uint32_t matchingCount = 0;
    uint32_t samplesTaken = 0;

    // Loop to take a fixed number of ADC samples.
    while(samplesTaken < sample_count)
    {
        // Read the ADC value for the given channel.
        // (Assume ADC_read() is implemented elsewhere in your project.)
        uint16_t reading = ADC_read(adc_channel);
        capacitorVoltage = reading;
        samplesTaken++;

        if(above)
        {
            if(reading >= threshold)
                matchingCount++;
        }
        else
        {
            if(reading <= threshold)
                matchingCount++;
        }
    }

    // Calculate the percentage of samples that met the condition.
    uint8_t percentage = (matchingCount * 100U) / samplesTaken;
    // Use FILTER_ACCURACY (e.g., defined as 70) from globals_and_gpio.h
    return (percentage >= FILTER_ACCURACY);
}

// Generic filter function to check GPIO stability with an expected state.
bool gpio_stability_filter(uint32_t duration_ms, uint8_t threshold_percentage, uint32_t gpio_pin, bool expected_state)
{
    uint32_t startTime = getSystemTime();
    uint32_t matchingCount = 0;
    uint32_t sampleCount = 0;

    while ((getSystemTime() - startTime) < duration_ms)
    {
        sampleCount++;
        bool pinState = GPIO_readPin(gpio_pin);
        if (pinState == expected_state)
        {
            matchingCount++;
        }
    }

    // Calculate the percentage of time the GPIO pin was in the expected state.
    uint8_t percentage = (matchingCount * 100) / sampleCount;

    return (percentage >= threshold_percentage);
}
