package sept24;

class Course {
    protected String courseCode;
    protected String courseTitle;
    protected int credit;

    protected double feePerCredit = 1000;

    public Course(String courseCode, String courseTitle, int credit) {
        this.courseCode = courseCode;
        this.courseTitle = courseTitle;
        this.credit = credit;
    }

    public void displayCourseInfo() {
        System.out.println("Course Code: " + courseCode);
        System.out.println("Course Title: " + courseTitle);
        System.out.println("Credit: " + credit);
        System.out.println("Course Fee: " + calculateCourseFee());
    }

    public double calculateCourseFee() {
        return credit * feePerCredit;
    }
}

class TheoryCourse extends Course {

    private int numberOfLectures;

    public TheoryCourse(String courseCode, String courseTitle, int credit, int numberOfLectures) {

        super(courseCode, courseTitle, credit);
        this.numberOfLectures = numberOfLectures;
    }

    public void displayTheoryDetails() {
        System.out.println("Number of Lectures: " + numberOfLectures);
    }

    @Override
    public double calculateCourseFee() {
        return (credit * feePerCredit) + 500;
    }
}

class LabCourse extends Course {

    private int numberOfLabHours;

    public LabCourse(String courseCode, String courseTitle, int credit, int numberOfLabHours) {

        super(courseCode, courseTitle, credit);
        this.numberOfLabHours = numberOfLabHours;
    }

    public void displayLabDetails() {
        System.out.println("Number of Lab Hours: " + numberOfLabHours);
    }

    @Override
    public double calculateCourseFee() {
        return (credit * feePerCredit) +
                (numberOfLabHours * 200);
    }
}

class CourseDemo {
    public static void main(String[] args) {

        TheoryCourse theoryCourse = new TheoryCourse(
                "CSE101",
                "Introduction to Programming",
                3,
                30);

        LabCourse labCourse = new LabCourse(
                "CSE102",
                "Programming Lab",
                2,
                20);

        System.out.println("----- Theory Course -----");
        theoryCourse.displayCourseInfo();
        theoryCourse.displayTheoryDetails();

        System.out.println();

        System.out.println("----- Lab Course -----");
        labCourse.displayCourseInfo();
        labCourse.displayLabDetails();
    }
}
