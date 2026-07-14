# Algorithms and Complexity Reference Guide

This guide describes common algorithms, recursion concepts, and performance complexity definitions.

---

## 1. Big-O Complexity Notation
Measures the upper bound of execution time or space relative to input size $N$.
- $O(1)$: Constant Time. Example: lookup key in dict.
- $O(\log N)$: Logarithmic Time. Example: Binary Search.
- $O(N)$: Linear Time. Example: search in unordered list.
- $O(N \log N)$: Linearithmic Time. Example: Merge Sort, Quick Sort.
- $O(N^2)$: Quadratic Time. Example: Bubble Sort, Nested loops.
- $O(2^N)$: Exponential Time. Example: naive recursive Fibonacci.

---

## 2. Classic Algorithms

### Binary Search
- Requirements: List must be sorted.
- Approach: Divide and conquer. Look at midpoint, narrow range to left or right half.
- Complexity: $O(\log N)$ time, $O(1)$ auxiliary space.

### Sorting Algorithms
- **Merge Sort**: Stable sort. Recursively divides array in halves, sorts halves, and merges. Complexity: $O(N \log N)$ time, $O(N)$ space.
- **Quick Sort**: Unstable sort. Selects pivot, partitions array around pivot, sorts recursively. Complexity: Average $O(N \log N)$, Worst $O(N^2)$ time.

---

## 3. Recursion & Dynamic Programming
- **Recursion**: A function calling itself. Requires:
  1. Base Case: stops recursion.
  2. Recursive Case: moves closer to the base case.
- **Dynamic Programming (DP)**: Solves complex problems by breaking them into overlapping subproblems, solving once, and storing solutions (memoization/tabulation) to avoid redundant computation.
