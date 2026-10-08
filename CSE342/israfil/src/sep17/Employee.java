package sep17;

/*
3. Create a class Employee with:
● name
● employeeId
● basicSalary
Create a constructor to initialize them. Create a method calculateSalary() that adds a 20%
allowance to the basic salary. Display the employee’s name, ID, and total salary.

*/
import java.util.Scanner;

public class Employee {
    private String name;
    private int employeeId;
    private double basicSalary;

    public Employee(String name, int employeeId, double basicSalary) {
        this.name = name;
        this.employeeId = employeeId;
        this.basicSalary = basicSalary;
    }

    public void calculateSalary() {
        double allowance = this.basicSalary * 0.20;
        double totalSalary = this.basicSalary + allowance;

        System.out.println("\n--- Employee Details ---");
        System.out.println("Employee Name : " + this.name);
        System.out.println("Employee ID   : " + this.employeeId);
        System.out.println("Total Salary  : $" + totalSalary + " (including 20% allowance)");
    }

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.print("Enter Employee Name: ");
        String name = scanner.nextLine();

        System.out.print("Enter Employee ID: ");
        int employeeId = scanner.nextInt();

        System.out.print("Enter Basic Salary: ");
        double basicSalary = scanner.nextDouble();

        Employee emp = new Employee(name, employeeId, basicSalary);

        emp.calculateSalary();

        scanner.close();
    }
}
