package sept24;

class Product {
    protected String name;
    protected double price;

    Product() {
        this.name = " ";
        this.price = 0.0;
    }

    public Product(String name, double price) {
        this.name = name;
        this.price = price;
    }

    public double calculatePrice() {
        return price;
    }

    public void displayProductInfo() {
        System.out.println("Product Name: " + name);
        System.out.println("Original Price: " + price);
        System.out.println("Final Price: " + calculatePrice());
    }
}

class Electronics extends Product {

    public Electronics(String name, double price) {
        super(name, price);
    }

    @Override
    public double calculatePrice() {
        return price - (price * 0.10);
    }
}

class Clothing extends Product {

    public Clothing(String name, double price) {
        super(name, price);
    }

    @Override
    public double calculatePrice() {
        return price - (price * 0.20);
    }
}

public class ProductDemo {
    public static void main(String[] args) {

        Electronics electronic = new Electronics("Laptop", 100000);

        Clothing clothing = new Clothing("Jacket", 5000);

        System.out.println("----- Electronics -----");
        electronic.displayProductInfo();

        System.out.println();

        System.out.println("----- Clothing -----");
        clothing.displayProductInfo();
    }
}
