public abstract class Person {
    private String name;
    private int age;
    private String contactNumber;

    // Default constructor
    public Person() {
        this.name = "Unknown";
        this.age = 0;
        this.contactNumber = "Unknown";
    }

    // Constructor with parameters
    public Person(String name, int age, String contactNumber) {
        this.name = name;
        this.age = age;
        this.contactNumber = contactNumber;
    }

    // Getters and setters
    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public int getAge() {
        return age;
    }

    public void setAge(int age) {
        this.age = age;
    }

    public String getContactNumber() {
        return contactNumber;
    }

    public void setContactNumber(String contactNumber) {
        this.contactNumber = contactNumber;
    }
}
