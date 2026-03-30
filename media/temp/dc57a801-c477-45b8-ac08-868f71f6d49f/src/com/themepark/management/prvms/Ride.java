package com.themepark.management.prvms;
import java.io.*;
import java.util.*;

/**
 * The Ride class implements RideInterface and overrides its methods
 * The required attribute Settings in Assessment 2 are satisfied
 * It provides empty and parameter constructors, as well as getters and setters to validate and read data.
 * To make the logic even more logical, we add the changeLastVisitors method to manage the state of the previous round of visitors.
 */
public class Ride implements RideInterface{
    // rollerCoaster carries 2 people at a time and enters history after playing, while thunderstorm carries 4 people at a time
    private String rideType;
    private Employee employee;
    private boolean operatingState;
    private int maxRider;
    private int numOfCycles;
    private Set<Visitor> onRideVisitor;
    private Queue<Visitor> visitorsQueue;
    private LinkedList<Visitor> rideVisitorHistory;

    // No-argument constructors
    public Ride(){}

    /**
     *
     * @param rideType: Represents the type of the ride
     * @param employee: Represents the operator of the ride
     * @param operatingState: Represents the status of the ride
     */
    public Ride(String rideType, Employee employee, boolean operatingState) {
        this.rideType = rideType;
        this.employee = employee;
        this.numOfCycles = 0;
        this.operatingState = operatingState;
        this.visitorsQueue = new LinkedList<>();
        this.rideVisitorHistory = new LinkedList<>();
        this.onRideVisitor = new LinkedHashSet<>();
        if(rideType.equals("Roller Coaster")){
            this.maxRider = 2;
        }
        else if(rideType.equals("Thunder Storm")){
            this.maxRider = 4;
;        }
        else{
            System.out.println("A Ride containing the number of seats was not found!");
        }
    }

    /**
     * Override the addVisitorToQueue method in the RideInterface
     * Main function 1: visitor objects that are not null are added to the queue
     * Main function 2: Modify the current tourist status to facilitate subsequent management
     * Main function 3: Print suitable success/failure messages.
     * @param visitor: Object Visitor to be added to the queue
     */
    @Override
    public void addVisitorToQueue(Visitor visitor){
        if (visitor != null){
            if(visitor.getPlayStatus().equals("Leisure"))
            {
                visitorsQueue.offer(visitor);
                visitor.setPlayStatus("On Queue");
                System.out.println("Visitor " + visitor.getFirstName() + " is successfully added to the queue!");
            }
            else{
                System.out.println("The current status of the visitor is " + visitor.getPlayStatus() + ", unable to join queue!");
            }
        }
        else {
            System.out.println("The visitor object is null and cannot join the queue!");
        }
    }

    /**
     * Override the removeVisitorFromQueue method in the RideInterface
     * Main function 1: The relationship between the actual tourists in the queue and maxRider is judged to ensure that when the number of tourists in the queue is less than maxRider, the Ride can also run normally.
     * Main function 2: Remove Visitor from the queue
     * Main function 3: Modify the status of the visitor, easy to manage
     */
    @Override
    public void removeVisitorFromQueue(){
        int actualRiders = visitorsQueue.size();
        if (actualRiders > maxRider){
            actualRiders = maxRider;
        }
        for (int i = 0; i < actualRiders; i++) {
            Visitor visitor = visitorsQueue.poll();
            if(visitor != null){
                visitor.setPlayStatus("On " + rideType);
                visitor.personalHistory(rideType);
                onRideVisitor.add(visitor);
                addVisitorToHistory(visitor);
                System.out.println("Visitor " + visitor.getFirstName() + "is successfully removed from the queue!");
            }
            else {
                System.out.println("The visitor object is null and cannot be modified!");
            }
        }
    }

    /**
     * This method is added to account for the possibility of a single visitor being removed.
     */
    public void removeOneVisitorFromQueue(){
        if (visitorsQueue == null || visitorsQueue.isEmpty()){
            System.out.println("The queue is null or empty!");
        }
        else {
            Visitor visitor = visitorsQueue.poll();
            if (visitor != null){
                System.out.println("Visitor " + visitor.getFirstName() + " is successfully removed from the queue!");
            }
            else{
                System.out.println("This visitor is null!");
            }
        }
    }

    /**
     * Override the printQueue method in the RideInterface
     * Main function 1: Loop through the Queue and print information about the visitor
     */
    @Override
    public void printQueue(){
        if (visitorsQueue.isEmpty()){
            System.out.println("There are no visitors in the queue!");
        }
        else {
            System.out.println("=============Start printing=============");
            for (Visitor visitor : visitorsQueue) {
                visitor.printInformation();
            }
            System.out.println("=============End of print=============");
        }
    }

    /**
     * Override the printQueue method in the RideInterface
     * Main function 1: The status of the operator currently riding is detected
     * Main function 2: Make a run of Ride using the relevant method
     */
    @Override
    public void runOneCycle(){
        if (employee == null || !employee.getEmployeeType().equals(rideType + " Operator") || !employee.isWorkingStatus()){
            System.out.println("The Ride cannot be run without an operator!");
            return;
        }
        if (visitorsQueue.isEmpty()){
            System.out.println("No one is currently queuing, so the Ride cannot run!");
            return;
        }
        changeLastVisitors();
        removeVisitorFromQueue();
        numOfCycles++;
    }

    /**
     * Override the addVisitorToHistory method in the RideInterface
     * Main function 1: Checks whether the visitor has been included in the history and is null
     * Main function 2: Add the visitor to the history
     * @param visitor: visitor to be added to the history
     */
    @Override
    public void addVisitorToHistory(Visitor visitor){
        if(visitor != null){
            if (rideVisitorHistory.contains(visitor)){
                System.out.println("The visitor is already included in the history.");
                return;
            }
            rideVisitorHistory.add(visitor);
            System.out.println("Visitor " + visitor.getFirstName() + " added successfully!");
        }
        else {
            System.out.println("The visitor object is null and cannot be added to the history!");
        }
    }

    /**
     * Override the checkVisitorFromHistory method in the RideInterface
     * Main function 1: The visitor that contains the input is detected from the history.
     * @param visitor: Visitor that need to be checked from the history
     */
    @Override
    public void checkVisitorFromHistory(Visitor visitor){
        if(visitor != null) {
            Iterator<Visitor> visitorIterator = rideVisitorHistory.iterator();
            while (visitorIterator.hasNext()){
                Visitor visitorHistory = visitorIterator.next();
                if (visitorHistory.equals(visitor)){
                    System.out.println("The visitor has been found with a total of " +
                            visitor.getPlayOfNumber()  +
                            " visits. Please check the visitor's personal history for details.");
                    return;
                }
            }
            System.out.println("The visitor was not found!");
        }
        else {
            System.out.println("The visitor object is null and cannot be checked!");
        }
    }

    /**
     * Override the numberOfVisitors method in the RideInterface
     * Main function 1: Returns the number of visitors in the history
     * @return The length of the LinkedList, that is, the number of visitors in the History.
     */
    @Override
    public int numberOfVisitors(){
        if (rideVisitorHistory == null){
            System.out.println("The history is null!");
            return 0;
        }
        return rideVisitorHistory.size();
    }

    /**
     * Override the printRideHistory method in the RideInterface
     * Main function 1: Check whether rideVisitorHistory is not null or empty.
     * Main function 2: Use iterator to print the history
     */
    @Override
    public void printRideHistory(){
        if (rideVisitorHistory == null || rideVisitorHistory.isEmpty()){
            System.out.println("The history is null or empty!");
        }
        else {
            Iterator<Visitor> visitorIterator = rideVisitorHistory.iterator();
            System.out.println("---" + rideType + " Visiting History" + "---");
            while (visitorIterator.hasNext()){
                Visitor visitor = visitorIterator.next();
                visitor.printInformation();
            }
        }
    }

    /**
     * The method outside the assignment requirement is used to modify the state of a visitor after riding the Ride
     */
    private void changeLastVisitors(){
        for (Visitor lastVisitor : onRideVisitor) {
            lastVisitor.setPlayStatus("Leisure");
        }
        onRideVisitor.clear();
    }

    /**
     * Sort the visitors in the history list that have ridden, sorting by ID and lastName
     */
    public void sortVisitor(){
        if (rideVisitorHistory == null || rideVisitorHistory.isEmpty()){
            System.out.println("The history list is null or empty");
            return;
        }
        try {
            rideVisitorHistory.sort(new VisitorComparator());
        } catch (ClassCastException e) {
            System.out.println("There is an error with the Visitor object");
        } catch (Exception e) {
            System.out.println("Error: " + e.getMessage());
        }
    }

    /**
     * The visitor information in the history is exported and stored in a CSV file
     * The exported information is the visitor's current ID, Name, Ticket Type and current status
     * Export the files to the backup package for easier management
     * !! This method cannot be called when the file is opened using software such as word because of threading
     */
    public void exportRideHistory(){
        String rideHistoryFilePath = "src/com/themepark/management/backup/rideHistory.csv";
        File file = new File(rideHistoryFilePath);
        try (FileWriter writer = new FileWriter(rideHistoryFilePath, true)) {
            if (file.length() == 0){
                writer.append("ID, First Name, Last Name, Phone Number, Play Status, Ticket Type\n");
            }
            for (Visitor visitor : rideVisitorHistory){
                writer.append(String.valueOf(visitor.getID())).append(", ")
                        .append(visitor.getFirstName()).append(", ")
                        .append(visitor.getLastName()).append(", ")
                        .append(visitor.getMobileNumber()).append(", ")
                        .append(visitor.getPlayStatus()).append(", ")
                        .append(visitor.getTicketType()).append("\n");
            }
            System.out.println("The history export was successful!");
        } catch (IOException e) {
            System.out.println("Error: " + e.getMessage());
            System.out.println("Go back to the current path and create rideHistory.csv");
        }

        rideHistoryFilePath = "rideHistory.csv";
        file = new File(rideHistoryFilePath);
        try (FileWriter fallbackWriter = new FileWriter(file, true)) {
            if (file.length() == 0) {
                fallbackWriter.append("ID, First Name, Last Name, Phone Number, Play Status, Ticket Type\n");
            }
            for (Visitor visitor : rideVisitorHistory) {
                fallbackWriter.append(String.valueOf(visitor.getID())).append(", ")
                        .append(visitor.getFirstName()).append(", ")
                        .append(visitor.getLastName()).append(", ")
                        .append(visitor.getMobileNumber()).append(", ")
                        .append(visitor.getPlayStatus()).append(", ")
                        .append(visitor.getTicketType()).append("\n");
            }
            System.out.println("The history export was successful in the current directory!");
        } catch (IOException fallbackException) {
            System.err.println("Rollback file write failure: " + fallbackException.getMessage());
            throw new RuntimeException(fallbackException);
        }
    }

    /**
     * Read the visitor history in a CSV file
     * The format as following:
     * ID: ***, Name: *** ***, Ticket Type: ***, Play Status: ***
     * !! This method cannot be called when the file is opened using software such as word because of threading
     */
    public void readRideHistory() {
        String rideHistoryFilePath = "src/com/themepark/management/backup/rideHistory.csv";
        File file = new File(rideHistoryFilePath);
        if (file.length() == 0 || !file.exists()) {
            System.out.println("The file does not exist or is empty and cannot be read! Rollback to rideHistory.csv");
            rideHistoryFilePath = "rideHistory.csv";
            file = new File(rideHistoryFilePath);
            if (file.length() == 0 || !file.exists()) {
                System.out.println("The file does not exist or is empty and cannot be read!");
                return;
            }
        }
        try (BufferedReader reader = new BufferedReader(new FileReader(rideHistoryFilePath))) {
            String lineRecord;
            reader.readLine();
            while ((lineRecord = reader.readLine()) != null) {
                String[] columns = lineRecord.split(",");
                if (columns.length == 6){
                    System.out.println("[ID: " + columns[0] + ", First Name: " + columns[1] + ", Last Name: " + columns[2]
                            + ", Phone Number: " + columns[3] + ", Play Status: " + columns[4] + ", Ticket Type: " + columns[5] + "]");
                }
            }
        } catch (IOException e) {
            System.out.println("Error: " + e.getMessage());
            throw new RuntimeException(e);
        }
    }

    /**
     * Main function: Read the history information from an existing file and store it in the history list of the Ride object
     */
    public void importRideHistory(){
        String rideHistoryFilePath = "src/com/themepark/management/backup/rideHistory.csv";
        File file = new File(rideHistoryFilePath);
        if (file.length() == 0 || !file.exists()) {
            System.out.println("The file does not exist or is empty and cannot be read! Rollback to rideHistory.csv");
            rideHistoryFilePath = "rideHistory.csv";
            file = new File(rideHistoryFilePath);
            if (file.length() == 0 || !file.exists()) {
                System.out.println("The file does not exist or is empty and cannot be read!");
                return;
            }
        }
        try (BufferedReader reader = new BufferedReader(new FileReader(rideHistoryFilePath))) {
            String lineRecord;
            reader.readLine();
            while ((lineRecord = reader.readLine()) != null) {
                String[] columns = lineRecord.split(",");
                if (columns.length == 6){
                    Visitor visitor = new Visitor(Integer.parseInt(columns[0].trim()),columns[1].trim(), columns[2].trim(), columns[3].trim(), columns[4].trim(), columns[5].trim());
                    addVisitorToHistory(visitor);
                }
            }
        } catch (IOException e) {
            System.out.println("Error: " + e.getMessage());
            throw new RuntimeException(e);
        }
    }

    // These are all getters and setters, some of which require data validation using regular expressions
    public String getRideType() {
        return rideType;
    }

    // Used to set the new ride type and verify that the ride type must be one of Roller Coaster and Thunder Storm
    public void setRideType(String rideType) {
        String rideTypeRegex = "Roller Coaster|Thunder Storm";
        if(!rideType.matches(rideTypeRegex)){
            System.out.println("Wrong Input: The ride status must be Roller Coaster and Thunder Storm!");
        }
        else {
            this.rideType = rideType;
        }
    }

    // Used to get the ride operator
    public Employee getEmployee() {
        return employee;
    }

    // Used to change the ride operator
    public void setEmployee(Employee employee) {
        if(employee != null){
            this.employee = employee;
            System.out.println("The current operator has been changed to " + employee.getFirstName());
        }
        else {
            System.out.println("Employee Object cannot be null!");
        }
    }

    // Used to get the operating state
    public boolean isOperatingState() {
        return operatingState;
    }

    // Used to update the operating state
    public void setOperatingState(boolean operatingState) {
        if (this.operatingState == operatingState){
            System.out.println("The current state is already " + operatingState);
        }
        else{
            this.operatingState = operatingState;
            System.out.println("The operating state is set to " + operatingState);
        }
    }

    // Used to get the visitorQueue
    public Queue<Visitor> getVisitorsQueue() {
        return visitorsQueue;
    }


    // Used to get the maxRider number
    public int getMaxRider() {
        return maxRider;
    }

    // Used to get the rideVisitorHistory
    public LinkedList<Visitor> getRideVisitorHistory(){return rideVisitorHistory;}

    // Used to get the numOfCycles
    public int getNumOfCycles() {
        return numOfCycles;
    }


}
