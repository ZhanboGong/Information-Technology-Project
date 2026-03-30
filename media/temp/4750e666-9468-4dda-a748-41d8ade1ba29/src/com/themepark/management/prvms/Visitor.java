package com.themepark.management.prvms;

import java.util.ArrayList;

/**
 * The Visitor class inherits from the abstract class Person
 * The attribute playStatus, ticketType, rideHistories and playOfNumber belonging to Visitor is extended
 * It provides empty and parameter constructors, as well as getters and setters to validate and read data.
 */
public class Visitor extends Person{

    private String playStatus;
    private String ticketType;
    private final ArrayList<String> rideHistories = new ArrayList<>();
    private int playOfNumber = 1;

    // No-argument constructors
    public Visitor(){super();}

    /**
     *
     * @param ID: Represents the ID of the Visitor(Person)
     * @param firstName: Represents the firstName of the Visitor(Person)
     * @param lastName: Represents the lastName of the Visitor(Person)
     * @param mobileNumber: Represents the Contact Phone Number of the Visitor(Person)
     * @param playStatus: Represents the playStatus of the Visitor
     * @param ticketType: Represents the ticketType of the Visitor
     */
    public Visitor(int ID, String firstName, String lastName, String mobileNumber, String playStatus, String ticketType){
        super(ID, firstName, lastName, mobileNumber);
        this.playStatus = playStatus;
        this.ticketType = ticketType;
    }

    /**
     * his is an abstract method on the Person class that prints information about the object
     */
    @Override
    public void printInformation(){
        System.out.println("================================");
        System.out.println("Visitor ID: " + ID);
        System.out.println("Visitor Name: " + firstName + " " + lastName);
        System.out.println("Contact: " + mobileNumber);
        System.out.println("Ticket Type: " + ticketType);
        System.out.println("Play Status: " + playStatus);
        System.out.println("================================");
    }

    /**
     * The history of each ride of the visitor is added to the personal history
     * @param rideType: The type of Ride the visitor is on
     */
    public void personalHistory(String rideType){
        String personalRecord = playOfNumber++ + ":" + rideType;
        rideHistories.add(personalRecord);
        System.out.println("Visitor" + ID + " added success to his or her personal history");
    }

    // Used to get the visitor play status
    public String getPlayStatus() {
        return playStatus;
    }

    // Used to set the new play status and verify that the play status must be one of Leisure, On Queue, On Roller Coaster and On Thunder Storm
    public void setPlayStatus(String playStatus) {
        String playStatusRegex = "Leisure|On Queue|On Roller Coaster|On Thunder Storm";
        if(!playStatus.matches(playStatusRegex)){
            System.out.println("Wrong Input: The play status must be Leisure, On Queue, On Roller Coaster, or On Thunder Storm!");
        }
        else{
            this.playStatus = playStatus;
        }
    }

    // Used to get the ticketType
    public String getTicketType() {
        return ticketType;
    }

    // Used to set the new play status and verify that the play status must be one of Children, Adult and Elder
    public void setTicketType(String ticketType) {
        String ticketTypeRegex = "Children|Adult|Elder";
        if(!ticketType.matches(ticketTypeRegex)){
            System.out.println("Wrong Input: The ticket type must be Children, Adult or Elder!");
        }
        else{
            this.ticketType = ticketType;
        }
    }

    // Used to get the play number
    public int getPlayOfNumber() {
        return playOfNumber - 1;
    }

    // Used to add 1 to the number of plays
    public void setPlayOfNumber(){
        this.playOfNumber++;
    }

    // Used to get the personal ride history
    public ArrayList<String> getRideHistories() {
        return rideHistories;
    }
}
