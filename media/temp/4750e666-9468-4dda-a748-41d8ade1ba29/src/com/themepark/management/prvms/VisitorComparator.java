package com.themepark.management.prvms;

import java.util.Comparator;

/**
 * The Comparator interface is implemented by overriding the compare method to first check if the ids are the same and, if so, compare lastName
 */
public class VisitorComparator implements Comparator<Visitor> {
    @Override
    public int compare(Visitor visitor1, Visitor visitor2) {
        if (visitor1.getID() < visitor2.getID()) {
            return -1;
        } else if (visitor1.getID() > visitor2.getID()) {
            return 1;
        } else {
            return visitor1.getLastName().compareTo(visitor2.getLastName());
        }
    }
}
