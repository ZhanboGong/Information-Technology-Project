package com.themepark.management.test;

import com.themepark.management.prvms.Employee;
import com.themepark.management.prvms.Person;
import com.themepark.management.prvms.Ride;
import com.themepark.management.prvms.Visitor;

public class AssessmentTwo {
    public static void main(String[] args) {
        // partThree();
        // partFourA();
        // partFourB();
        //partFive();
        // partSix();
        //partSeven();
    }
    public static void partThree(){
        // Create five Visitor object and an employee object
        Visitor visitor1 = new Visitor(1, "Zhanbo", "Gong", "1234567890", "Leisure", "Children");
        Visitor visitor2 = new Visitor(2, "Stephen", "Curry", "2233 223 223", "Leisure", "Adult");
        Visitor visitor3 = new Visitor(3, "Li", "Tian", "1123112312", "Leisure", "Adult");
        Visitor visitor4 = new Visitor(4, "Lionel", "Messi", "1145141234", "Leisure", "Adult");
        Visitor visitor5 = new Visitor(5, "JiaShuo", "Gao", "1122334455", "Leisure", "Elder");
        Employee employee1 = new Employee(11, "San", "Zhang", "5544332211", "Roller Coaster Operator", true);
        // Create a new Ride Object
        Ride ride1 = new Ride("Roller Coaster", employee1, true);
        // Add 5 Visitors to the Queue.
        ride1.addVisitorToQueue(visitor1);
        ride1.addVisitorToQueue(visitor2);
        ride1.addVisitorToQueue(visitor3);
        ride1.addVisitorToQueue(visitor4);
        ride1.addVisitorToQueue(visitor5);
        // Remove a Visitor from the Queue
        ride1.removeOneVisitorFromQueue();
        // Print all Visitors in the Queue
        ride1.printQueue();
    }
    public static void partFourA(){
        // Create five Visitor object and an employee object
        Visitor visitor1 = new Visitor(1, "Zhanbo", "Gong", "1234567890", "Leisure", "Children");
        Visitor visitor2 = new Visitor(2, "Stephen", "Curry", "2233 223 223", "Leisure", "Adult");
        Visitor visitor3 = new Visitor(3, "Li", "Tian", "1123112312", "Leisure", "Adult");
        Visitor visitor4 = new Visitor(4, "Lionel", "Messi", "1145141234", "Leisure", "Adult");
        Visitor visitor5 = new Visitor(5, "JiaShuo", "Gao", "1122334455", "Leisure", "Elder");
        Employee employee1 = new Employee(11, "San", "Zhang", "5544332211", "Roller Coaster Operator", true);
        // Create a new Ride Object
        Ride ride1 = new Ride("Roller Coaster", employee1, true);
        // Add 5 Visitors to the collection
        ride1.addVisitorToHistory(visitor1);
        ride1.addVisitorToHistory(visitor2);
        ride1.addVisitorToHistory(visitor3);
        ride1.addVisitorToHistory(visitor4);
        ride1.addVisitorToHistory(visitor5);
        // Check if a Visitor is in the collection
        ride1.checkVisitorFromHistory(visitor1);
        // Print the number of Visitors in the collection
        System.out.println(ride1.numberOfVisitors());
        // Print all Visitors in the collection
        ride1.printRideHistory();
    }
    public static void partFourB(){
        // Create five Visitor object and an employee object
        Visitor visitor1 = new Visitor(1, "Zhanbo", "Gong", "1234567890", "Leisure", "Children");
        Visitor visitor2 = new Visitor(2, "Stephen", "Curry", "2233 223 223", "Leisure", "Adult");
        Visitor visitor3 = new Visitor(3, "Li", "Tian", "1123112312", "Leisure", "Adult");
        Visitor visitor4 = new Visitor(4, "Lionel", "Messi", "1145141234", "Leisure", "Adult");
        Visitor visitor5 = new Visitor(5, "JiaShuo", "Gao", "1122334455", "Leisure", "Elder");
        Employee employee1 = new Employee(11, "San", "Zhang", "5544332211", "Roller Coaster Operator", true);
        // Create a new Ride Object
        Ride ride1 = new Ride("Roller Coaster", employee1, true);
        // Add 5 Visitors to the collection(Adding the collection out of order)
        ride1.addVisitorToHistory(visitor5);
        ride1.addVisitorToHistory(visitor3);
        ride1.addVisitorToHistory(visitor1);
        ride1.addVisitorToHistory(visitor2);
        ride1.addVisitorToHistory(visitor4);
        // Print before sorting
        ride1.printRideHistory();
        // Sort the collection
        ride1.sortVisitor();
        // Print after sorting
        ride1.printRideHistory();

    }
    public static void partFive(){
        // Create ten Visitor object and an employee object
        Visitor visitor1 = new Visitor(1, "Zhanbo", "Gong", "1234567890", "Leisure", "Children");
        Visitor visitor2 = new Visitor(2, "Stephen", "Curry", "2233 223 223", "Leisure", "Adult");
        Visitor visitor3 = new Visitor(3, "Li", "Tian", "1123112312", "Leisure", "Adult");
        Visitor visitor4 = new Visitor(4, "Lionel", "Messi", "1145141234", "Leisure", "Adult");
        Visitor visitor5 = new Visitor(5, "JiaShuo", "Gao", "1122334455", "Leisure", "Elder");
        Visitor visitor6 = new Visitor(6, "Caleb", "Gong", "1817900000", "Leisure", "Adult");
        Visitor visitor7 = new Visitor(7, "Jingyu", "Zhang", "19899990101", "Leisure", "Children");
        Visitor visitor8 = new Visitor(8, "Si", "Li", "9876543210", "Leisure", "Elder");
        Visitor visitor9 = new Visitor(9, "Er", "Wang", "7776665550", "Leisure", "Elder");
        Visitor visitor10 = new Visitor(10, "Zi", "Ma", "1370780765", "Leisure", "Children");
        Employee employee1 = new Employee(11, "San", "Zhang", "5544332211", "Roller Coaster Operator", true);
        // Create a new Ride Object
        Ride ride1 = new Ride("Roller Coaster", employee1, true);
        // Add a minimum of 10 Visitors to the Queue
        ride1.addVisitorToQueue(visitor1);
        ride1.addVisitorToQueue(visitor2);
        ride1.addVisitorToQueue(visitor3);
        ride1.addVisitorToQueue(visitor4);
        ride1.addVisitorToQueue(visitor5);
        ride1.addVisitorToQueue(visitor6);
        ride1.addVisitorToQueue(visitor7);
        ride1.addVisitorToQueue(visitor8);
        ride1.addVisitorToQueue(visitor9);
        ride1.addVisitorToQueue(visitor10);
        // Print all Visitors in the queue.
        ride1.printQueue();
        // Run one cycle
        ride1.runOneCycle();
        // Print all Visitors in the queue after one cycle is run
        ride1.printQueue();
        // Print all Visitors in the collection.
        ride1.printRideHistory();
    }
    public static void partSix(){
        // Create five visitors and an new employee
        Visitor visitor1 = new Visitor(1, "Zhanbo", "Gong", "1234567890", "Leisure", "Children");
        Visitor visitor2 = new Visitor(2, "Stephen", "Curry", "2233 223 223", "Leisure", "Adult");
        Visitor visitor3 = new Visitor(3, "Li", "Tian", "1123112312", "Leisure", "Adult");
        Visitor visitor4 = new Visitor(4, "Lionel", "Messi", "1145141234", "Leisure", "Adult");
        Visitor visitor5 = new Visitor(5, "JiaShuo", "Gao", "1122334455", "Leisure", "Elder");
        Employee employee1 = new Employee(11, "San", "Zhang", "5544332211", "Roller Coaster Operator", true);
        // Create a new Ride
        Ride ride1 = new Ride("Roller Coaster", employee1, true);
        // Add five Visitors to the Ride History List
        ride1.addVisitorToHistory(visitor1);
        ride1.addVisitorToHistory(visitor2);
        ride1.addVisitorToHistory(visitor3);
        ride1.addVisitorToHistory(visitor4);
        ride1.addVisitorToHistory(visitor5);
        // Export the Visitors to a file
        ride1.exportRideHistory();
    }
    public static void partSeven(){
        // Create an employee
        Employee employee1 = new Employee(11, "San", "Zhang", "5544332211", "Roller Coaster Operator", true);
        // Create a new Ride
        Ride ride1 = new Ride("Roller Coaster", employee1, true);
        // import the file
        ride1.importRideHistory();
        // print the Visitor number
        System.out.println(ride1.numberOfVisitors());
        // print Visitor History List
        ride1.printRideHistory();
    }
}
