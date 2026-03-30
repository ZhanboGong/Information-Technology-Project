package com.themepark.management.prvms;

public interface RideInterface {

    public void addVisitorToQueue(Visitor visitor);
    public void removeVisitorFromQueue();
    public void printQueue();
    public void runOneCycle();
    public void addVisitorToHistory(Visitor visitor);
    public void checkVisitorFromHistory(Visitor visitor);
    public int numberOfVisitors();
    public void printRideHistory();
}
