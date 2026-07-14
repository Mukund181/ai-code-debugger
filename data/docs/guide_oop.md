# Object-Oriented Programming (OOP) in Python Guide

This guide details Python OOP design principles, structure, and implementation styles.

---

## 1. Classes & Objects
- A **Class** is a blueprint/template for creating objects.
- An **Object** is an instance of a class, holding actual data and behaviors.
- The `__init__` constructor method initializes instance variables when a new object is created.
- The `self` parameter represents the current instance of the object.

---

## 2. The Four Pillars of OOP

### 1. Inheritance
Enables a class (child/subclass) to inherit attributes and methods from another class (parent/superclass).
- Syntax: `class ChildClass(ParentClass):`
- Use the `super()` function to invoke methods from the parent class.

### 2. Polymorphism
Allows different classes to define methods with the same name but different behaviors. For instance, `Dog.make_sound()` prints "Bark", while `Cat.make_sound()` prints "Meow".

### 3. Encapsulation
Restricts direct access to some of an object's components. In Python, prefixing an attribute with double underscores (`__`) triggers name mangling, simulating private attributes. Use getter and setter methods to access private attributes.

### 4. Abstraction
Hides complex implementation details and exposes only essential features. Implemented using python's `abc` module and `abstractmethod` decorator to define abstract base classes.
