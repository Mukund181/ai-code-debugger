# Python Data Structures Reference Guide

This guide covers common python data structures, their performance characteristics, and when to use them.

---

## 1. Sequences: Lists & Tuples
- **Lists** (`[1, 2, 3]`): Dynamic arrays. Ideal for sequential collections. Elements can be added, modified, or removed.
  - Append: $O(1)$ amortized.
  - Insert/Delete (arbitrary position): $O(N)$.
  - Lookup by index: $O(1)$.
- **Tuples** (`(1, 2, 3)`): Immutable sequences. Used to group heterogeneous data. Safer than lists for read-only static sequences and can be used as dictionary keys.

---

## 2. Key-Value Mappings: Dictionaries
- **Dictionaries** (`{"key": "value"}`): Hash table implementation.
  - Average Case Lookup/Insert/Delete: $O(1)$.
  - Worst Case (high hash collision): $O(N)$.
  - Ideal for rapid indexing and lookup. Use `.get(key, default)` for error-resilient fetches.

---

## 3. Uniqueness: Sets
- **Sets** (`{1, 2, 3}`): Collections of unique, unordered, hashable items. Under the hood, sets use hash tables.
  - Add/Check membership: $O(1)$ average.
  - Ideal for deduplication and performing mathematical operations like intersection, union, and difference.

---

## 4. Advanced Structures: Stacks, Queues, Graphs, Trees
- **Stacks** (LIFO - Last In First Out): Use python's `collections.deque` or lists with `append()` and `pop()`.
- **Queues** (FIFO - First In First Out): Use `collections.deque` with `append()` and `popleft()`.
- **Trees**: Node-based hierarchy. Binary Search Trees (BST) provide average $O(\log N)$ search time.
- **Graphs**: Nodes and edges. Can be represented using adjacency lists (a dictionary of lists or sets).
