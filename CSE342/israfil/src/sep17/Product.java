package sep17;

/*
2. Create a class Product with:
● productName
● price
● quantity
Use a constructor to initialize the values. Create a method calculateTotal() that returns:Total
price of a product. Create another method calculateDiscount() that gives a 10% discount if the
total price is greater than 5000. */
import java.util.Scanner;

public class Product {
    public String productName;
    public double price;
    public int quantity;

    Product() {
        this.productName = null;
        this.price = 0;
        this.quantity = 0;
    }

    Product(String prodname, double price, int quantity) {
        this.productName = prodname;
        this.price = price;
        this.quantity = quantity;
    }

    public double calculateTotal() {
        double totalprice = this.price * this.quantity;
        return totalprice;
    }

    public double calculateDiscount() {
        double total = calculateTotal();
        if (total > 5000) {
            return total * 0.10;
        }
        return 0;
    }

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);

        System.out.print("Enter product name: ");
        String name = scanner.nextLine();

        System.out.print("Enter price: ");
        double price = scanner.nextDouble();

        System.out.print("Enter quantity: ");
        int quantity = scanner.nextInt();

        Product product = new Product(name, price, quantity);

        double total = product.calculateTotal();
        double discount = product.calculateDiscount();
        double finalPrice = total - discount;

        System.out.println("\n--- Product Receipt ---");
        System.out.println("Product Name: " + product.productName);
        System.out.println("Total Price: $" + total);
        System.out.println("Discount: $" + discount);
        System.out.println("Final Price: $" + finalPrice);

        scanner.close();
    }
}
