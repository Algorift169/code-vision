package sep17;

import java.util.Scanner;

class Student {
    public String name;
    public String id;

    public double fee = 0.0;
    public double monthly = 0.0;

    public Student() {
        this.name = " ";
        this.id = " ";
    }

    public Student(String n, String id, double mn) {
        this.name = n;
        this.id = id;
        this.monthly = mn;
    }

    // Overloaded constructor...
    public Student(String id, String name) {
        this.name = name;
        this.id = id;
    }

    public void fee() {
        this.fee = this.monthly * 12;
        // return this.fee;
    }

    public void display() {
        System.out.println("Student Name: " + this.name);
        System.out.println("ID: " + this.id);
        System.out.println("Annual Fee: " + this.fee);
    }
}

public class demo {
    public static void main(String[] args) {

        Student s1 = new Student();
        Student s2 = new Student("147", "Israfil");
        Scanner in = new Scanner(System.in);

        System.out.println("____________________________");

        System.out.print("Enter student name: ");
        s1.name = in.nextLine();

        System.out.print("Enter student ID: ");
        s1.id = in.nextLine();

        System.out.print("Enter monthly fee: ");
        s1.monthly = in.nextDouble();

        // Calculate annual fee for S1
        s1.fee();

        System.out.println("____________________________");

        // Display S2
        System.out.println("Object S2:");
        s2.display();

        System.out.println("____________________________");

        // Display S1
        System.out.println("Object S1:");
        s1.display();

        in.close();
    }

}
