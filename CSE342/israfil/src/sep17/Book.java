package sep17;

import java.util.Scanner;

class Book {
    String title;
    String author;
    double price;

    Book() {
        title = "Unknown";
        author = "Unknown";
        price = 0;
    }

    Book(String title, String author) {
        this.title = title;
        this.author = author;
        price = 0;
    }

    Book(String title, String author, double price) {
        this.title = title;
        this.author = author;
        this.price = price;
    }

    void displayBook() {
        System.out.println("Title: " + title);
        System.out.println("Author: " + author);
        System.out.println("Price: " + price);
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        System.out.print("Enter title: ");
        String title = sc.nextLine();

        System.out.print("Enter author: ");
        String author = sc.nextLine();

        System.out.print("Enter price: ");
        double price = sc.nextDouble();

        Book book = new Book(title, author, price);

        System.out.println("\nBook Details:");
        book.displayBook();

        sc.close();
    }
}
