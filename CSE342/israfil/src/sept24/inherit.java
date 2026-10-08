package sept24;

class Person {
    String name;
    String addr;
    double basicSalary;

    Person() {
        this.name = " ";
        this.addr = " ";
        this.basicSalary = 0.0;
    }

    Person(String name, String addr, double bs) {
        this.name = name;
        this.addr = addr;
        this.basicSalary = bs;
    }

    public double calSal(double bs, double alw) {
        return bs + alw;
    }

    public void display() {
        System.out.println("Name: " + this.name);
        System.out.println("Address: " + this.addr);
    }
}

class Teacher extends Person {
    String tid;
    double allw = 20000;

    Teacher(String name, String addr, String tid) {
        super(name, addr, 40000);
        this.tid = tid;
    }

    @Override
    public void display() {
        super.display();
        System.out.println("Teacher ID: " + this.tid);
        System.out.println("Total Salary: " + calSal(basicSalary, allw));
    }
}

class Employee extends Person {
    String eid;
    double alw = 20000;

    Employee(String name, String addr, String eid) {
        super(name, addr, 30000);
        this.eid = eid;
    }

    @Override
    public void display() {
        super.display();
        System.out.println("Employee ID: " + this.eid);
        System.out.println("Total Salary: " + calSal(basicSalary, alw));
    }
}

public class inherit {
    public static void main(String[] args) {
        Teacher t1 = new Teacher("Israfil", "Mirpur", "1234");
        Employee e1 = new Employee("Sadik", "Mirpur", "5664");

        t1.display();
        System.out.println("----------------------------------------------------");

        e1.display();
    }
}
