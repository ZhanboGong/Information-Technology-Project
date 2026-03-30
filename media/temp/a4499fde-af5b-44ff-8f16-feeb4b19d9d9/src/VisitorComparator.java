import java.util.Comparator;

public class VisitorComparator implements Comparator<Visitor> {

    @Override
    public int compare(Visitor v1, Visitor v2) {
        // 先按年龄排序，如果年龄相同，再按票种类排序
        int ageComparison = Integer.compare(v1.getAge(), v2.getAge());
        if (ageComparison != 0) {
            return ageComparison;
        } else {
            return v1.getTicketType().compareTo(v2.getTicketType());
        }
    }
}
