package com.themepark.management.prvms;

/**
 * The Person class is an abstract class
 * Contains the base properties ID, firstName, lastName, and mobileNumber
 * This class is inherited by the Employee and Visitor classes
 */
public abstract class Person {
    protected int ID;
    protected String firstName;
    protected String lastName;
    protected String mobileNumber;

    // No-argument Constructors
    public Person(){}

    /**
     *
     * @param ID: Represents the ID of the Person
     * @param firstName: Represents the firstName of the Person
     * @param lastName: Represents the lastName of the Person
     * @param mobileNumber: Represents the Contact Phone Number of the Person
     */
    public Person(int ID, String firstName, String lastName, String mobileNumber) {
        this.ID = ID;
        this.firstName = firstName;
        this.lastName = lastName;
        this.mobileNumber = mobileNumber;
    }

    // Used to get the Person ID
    public int getID() {
        return ID;
    }

    // Used to update the Person ID
    public void setID(int ID) {
        if (ID < 0) {
            System.out.println("The Person ID must be positive integer");
            return;
        }
        this.ID = ID;
        System.out.println("The person's ID is updated to " + ID);
    }

    /**
     * This is an abstract method on the Person class that prints information about the object
     */
    public abstract void printInformation();

    // Used to get the Person's firstname
    public String getFirstName() {
        return firstName;
    }

    // Used to update the Person's firstname
    // Use a regular expression to validate the data,
    // ensuring that the first letter is uppercase and all subsequent letters are lowercase, and that no other symbols are included
    public void setFirstName(String firstName) {
        String firstNameRegex = "[A-Z][a-z]*";
        if(firstName == null || firstName.trim().isEmpty()){
            System.out.println("Name must be in the following format: Initial(A-Z) Follow-up(a-z)");
        } else if (!firstName.matches(firstNameRegex)) {
            System.out.println("The first name must begin with an uppercase letter and follow with a lowercase letter!");
        }
        else {
            this.firstName = firstName;
            System.out.println("First Name is set to " + firstName);
        }
    }

    // Used to get the Person's lastname
    public String getLastName() {

        return lastName;
    }

    // Used to update the Person's lastname
    public void setLastName(String lastName) {
        String lastNameRegex = "[A-Z][a-z]*";
        if(lastName == null || lastName.trim().isEmpty()){
            System.out.println("Name must be in the following format: Initial(A-Z) Follow-up(a-z)");
        } else if (!lastName.matches(lastNameRegex)) {
            System.out.println("The last name must begin with an uppercase letter and follow with a lowercase letter!");
        }
        else {
            this.lastName = lastName;
            System.out.println("Last Name is set to " + lastName);
        }
    }

    // Used to get the mobile number
    public String getMobileNumber() {
        return mobileNumber;
    }

    //After searching on the Internet, the format of landline telephones in Australia is (0X) XXXX XXXX,
    // and the format of mobile telephones is 04XX XXX XXX,
    // so regular expressions are used to verify the data of the phone number entered or updated
    public void setMobileNumber(String mobileNumber) {
        String mobileRegex = "0\\d[ -]?\\d{2}[ -]?\\d{2}[ -]?\\d[ -]?\\d{3}";
        if(mobileNumber == null || mobileNumber.trim().isEmpty())
        {
            System.out.println("Wrong Input: Mobile number cannot be empty and null!");
        }
        else if (!mobileNumber.matches(mobileRegex)) {
            System.out.println("Wrong Input: Phone numbers are nine or ten digits long!");
        }
        else{
            this.mobileNumber = mobileNumber;
            System.out.println("Mobile Number is set to " + mobileNumber);
        }
    }
}
