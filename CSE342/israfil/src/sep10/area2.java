package sep10;

import java.util.Scanner;

public class area2 {
public static void main(String[] args) {

    Scanner input = new Scanner(System.in);

    System.out.print("Enter length: ");
    double length = input.nextDouble();

    System.out.print("Enter height: ");
    double height = input.nextDouble();

    double area = 0.5 * length * height;

    System.out.println("Area of rectangle = " + area);

    input.close();
}
}
