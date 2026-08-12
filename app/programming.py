#this fun add two numbers
def add_numbers(a, b):
    return a + b
#this fun subtract two numbers
def subtract_numbers(a, b):
    return a - b
#this fun multiply two numbers
def multiply_numbers(a, b):
    return a * b
#this fun divide two numbers
def divide_numbers(a, b):
    return a / b

print("This is a simple calculator program.")
print("Select operation:")
print("1. Add")
print("2. Subtract")
print("3. Multiply")
print("4. Divide")
while True:
    choice = input("Enter choice(1/2/3/4): ")
    if choice in ('1', '2', '3', '4'):
        num1 = float(input("Enter first number: "))
        num2 = float(input("Enter second number: "))
        if choice == '1':
            print(num1, "+", num2, "=", add_numbers(num1, num2))
        elif choice == '2':
            print(num1, "-", num2, "=", subtract_numbers(num1, num2))
        elif choice == '3':
            print(num1, "*", num2, "=", multiply_numbers(num1, num2))
        elif choice == '4':
            if num2 != 0:
                print(num1, "/", num2, "=", divide_numbers(num1, num2))
            else:
                print("Error! Division by zero.")
        next_calculation = input("Do you want to perform another calculation? (yes/no): ")
        if next_calculation.lower() != 'yes':
            break
    else:
        print("Invalid Input")