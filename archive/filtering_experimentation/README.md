# Signal Filtering Analysis and Methodology

This document outlines the iterative process of developing a robust signal filtering and analysis tool for processing noisy sawtooth wave data from CSV files.

## 1. Project Goal

The initial goal was to apply various smoothing filters to noisy signal data to reduce noise while preserving the sharp transitions characteristic of a sawtooth wave. The effectiveness of these filters would be evaluated to find the best approach.

## 2. Initial Approach: Visual Comparison

Our first step was to apply a set of standard time-domain filters to the data:

- **Moving Average:** Simple but prone to smearing sharp features.
- **Median Filter:** Effective at removing sharp, outlier peaks (salt-and-pepper noise).
- **Butterworth (Low-pass):** A standard frequency-based filter good for general smoothing.
- **Gaussian Filter:** Provides smooth results by using weighted averages.

These filters were plotted against the original signal for a simple visual comparison. While useful, this method was subjective and lacked a quantitative basis for choosing the "best" filter.

## 3. Quantitative Analysis: The Combined Score

To move beyond subjective visual analysis, we developed a quantitative scoring system. This evolved in two stages:

### Stage A: Root Mean Squared Error (RMSE)

We first introduced RMSE to measure the "goodness of fit." However, we quickly realized that a filter that is very faithful to the noisy signal (low RMSE) is not necessarily a *good* filter, as it might not be smooth enough.

### Stage B: The Combined Score

This led to the development of a more sophisticated, two-part scoring metric that could be balanced with a tuning parameter, `lambda (λ)`.

**Combined Score = Fidelity (SSR) + λ * Roughness**

1.  **Fidelity (SSR - Sum of Squared Residuals):** Calculated as `sum((original - filtered)^2)`. This measures how much the filtered signal deviates from the original. A lower SSR means higher fidelity.

2.  **Roughness:** Calculated as the sum of the squared second derivative, `sum(diff(filtered, 2)^2)`. This is a measure of the signal's smoothness. A perfectly smooth, straight line would have a roughness of zero. A lower value means the signal is smoother.

3.  **Lambda (λ):** This crucial parameter allows us to tune the balance between fidelity and smoothness. 
    - A **low lambda** (e.g., 1.0) prioritizes a close fit to the original data.
    - A **high lambda** (e.g., 10.0, 30.0) penalizes roughness more heavily, forcing the selection of a smoother filter, even if it deviates more from the original noisy signal.

## 4. Advanced Technique: Hybrid Filtering

We observed that for signals with very sharp, tall outlier peaks, standard linear filters (like Gaussian or Butterworth) were insufficient. They would always be influenced by the peak, leaving a "bump" in the smoothed data.

To solve this, we implemented a **hybrid (or "chained") filter** approach:

1.  **First Pass (Outlier Rejection):** A **Median Filter** is applied first. Its non-linear nature allows it to effectively ignore and remove sharp spikes from the data.
2.  **Second Pass (General Smoothing):** A second filter (e.g., Gaussian or Savitzky-Golay) is then applied to the much cleaner output of the median filter to smooth out the remaining general noise.

## 5. Final Implementation: Automated Parameter Search

Combining these concepts, the final script evolved into a powerful, automated tool that:

1.  Pre-processes a signal with a **Median Filter**.
2.  Performs a **grid search** on the pre-processed signal, testing a wide range of parameters for Butterworth, Gaussian, and Savitzky-Golay filters.
3.  Uses the **Combined Score** to evaluate and rank every single filter chain.
4.  Allows for looping through multiple `lambda` values to find the optimal balance for a given dataset.

Through this comprehensive search, we determined the following default filter chain to be a robust choice:

- **Lambda (λ):** 1.0
- **Filter Chain:** `Median Filter (kernel=5)` -> `Savitzky-Golay Filter (window=9, order=2)`

This process demonstrates a complete workflow from a simple problem to a sophisticated, data-driven solution.