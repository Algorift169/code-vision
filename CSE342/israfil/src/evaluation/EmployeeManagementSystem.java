package evaluation;

class Employee{
    String id;
    String name;
    double basicSalary;

    public Employee() {
        this.id = " ";
        this.name = " ";
        this.basicSalary = 0.0;
    }

    public Employee(String name, String id, double basicSalary){
        this.name = name;
        this.id = id;
        this.basicSalary = basicSalary;
    }

    public double  calculateSalary(int dummy){
        return  this.basicSalary;
    }

    public void displayInfo() {
        System.out.println("Employee nameL: " + this.name);
        System.out.println("Employee id : " + this.id);
        System.out.println("Basic Salary: " + this.basicSalary);
    }

    
}

class AdministrativeStaff extends Employee{
    String department;
    int workingHours;

    public AdministrativeStaff() {
        this.department = " ";
        this.workingHours= 0;
    }

    public AdministrativeStaff(String name, String id, double basicSalary, String department, int workingHours){
        super(name,id,basicSalary);
        this.department = department;
        this.workingHours = workingHours;
    }

    @Override 
        public double  calculateSalary(int dummy){
       // int regular = 40;
        int overtime_rate_perHour = 500;

        if(dummy > 40){
            return this.basicSalary + (40 - dummy) * overtime_rate_perHour;
        }

        return this.basicSalary;
    }
    @Override
        public void displayInfo() {
        System.out.println("Employee nameL: " + this.name);
        System.out.println("Employee id : " + this.id);
        System.out.println("Basic Salary: " + this.basicSalary);
        System.out.println("Department: "+ this.department);
        System.out.println("Working Hour: " + this.workingHours);
    }
}

public class EmployeeManagementSystem {
    public static void main(String[] args) {
        AdministrativeStaff a1 = new AdministrativeStaff("Israfil", "147", 10000, "CSE", 30);
        a1.displayInfo();   
        AdministrativeStaff a2 = new AdministrativeStaff("Israfil", "147", 10000, "CSE", 40);
        a2.displayInfo();
        System.out.println("A2 has extra vfee of : "+ a2.calculateSalary(47));
    }
}
