package com.themepark.management.prvms;

/**
 * The Employee class inherits from the abstract class Person
 * The attribute employeeType and workingStatus belonging to Employee is extended
 * It provides empty and parameter constructors, as well as getters and setters to validate and read data.
 */
public class Employee extends Person{
    // Used to represent the type of employee, the system includes Roller Coaster Operator and Thunder Storm Operator
    private String employeeType;
    // Use a Boolean value to indicate whether an employee is on duty or not
    private boolean workingStatus;
    // No-argument constructors
    public Employee(){super();}

    /**
     *
     * @param ID: Represents the ID of the Employee(Person)
     * @param firstName: Represents the firstName of the Employee(Person)
     * @param lastName: Represents the lastName of the Employee(Person)
     * @param mobileNumber: Represents the Contact Phone Number of the Employee(Person)
     * @param employeeType: Represents the type of the Employee
     * @param workingStatus: Represents whether the employee is on duty or not now
     */
    public Employee(int ID, String firstName, String lastName, String mobileNumber, String employeeType, boolean workingStatus){
        super(ID, firstName, lastName, mobileNumber);
        this.employeeType = employeeType;
        this.workingStatus = workingStatus;
    }

    /**
     * This is an abstract method on the Person class that prints information about the object
     */
    @Override
    public void printInformation(){
        System.out.println("================================");
        System.out.println("ID: " + ID);
        System.out.println("Employee Name: " + firstName + " " + lastName);
        System.out.println("Contact: "+ mobileNumber);
        System.out.println("Employee Type: " + employeeType);
        System.out.println("Working Status: " + workingStatus);
        System.out.println("================================");
    }

    // Used to get an Employee Type
    public String getEmployeeType() {
        return employeeType;
    }

    // Used to set the new employee type and verify that the employee type must be one of Roller Coaster Operator and Thunder Storm Operator
    public void setEmployeeType(String employeeType) {
        String employeeTypeRegex = "Roller Coaster Operator|Thunder Storm Operator";
        if (!employeeType.matches(employeeTypeRegex)){
            System.out.println("Wrong Input: The employee type must be Roller Coaster Operator and Thunder Storm Operator!");
        }
        else {
            this.employeeType = employeeType;
            System.out.println("Employee" + ID + "'s type is updated to " + employeeType);
        }
    }

    // Used to get the workingStatus
    public boolean isWorkingStatus() {
        return workingStatus;
    }

    // Used to set the new workingStatus
    public void setWorkingStatus(boolean workingStatus) {
        if (this.workingStatus == workingStatus){
            System.out.println("The working state of Employee" + ID + " is already " + workingStatus);
        }
        else {
            this.workingStatus = workingStatus;
            System.out.println("Employee" + ID + "'s workingStatus is updated to " + workingStatus);
        }
    }
}
