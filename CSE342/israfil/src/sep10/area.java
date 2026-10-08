package sep10;

import java.util.Scanner;

public class area {
public static void main(String[] args) {

    Scanner input = new Scanner(System.in);

    System.out.print("Enter length: ");
    double length = input.nextDouble();

    System.out.print("Enter width: ");
    double width = input.nextDouble();

    double area = length * width;

    System.out.println("Area of rectangle = " + area);

    input.close();
}
}
