package sep10;

import java.util.Scanner;

public class arry {
    public static void main(String[] args) {
        Scanner input = new Scanner(System.in);
        int[] arr = new int[5];
        System.out.println("Enetr array eloements: ");
        for (int i = 0; i < arr.length; i++) {
            arr[i] = input.nextInt();
        }

        System.out.println("array elements: ");
        for (int i = 0; i < arr.length; i++) {
            System.out.println(arr[i] + " ");
        }

        int max = 0, min = arr[0];

        for (int i = 0; i < arr.length; i++) {
            if (arr[i] > max)
                max = arr[i];
        }

        for (int i = 0; i < arr.length; i++) {
            if (arr[i] < min)
                min = arr[i];
        }

        System.out.println("Max: " + max + "\nMin: " + min);

        input.close();
    }
}