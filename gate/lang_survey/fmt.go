package main
import ("bufio"; "fmt"; "os"; "strconv"; "strings")
func main() { sc := bufio.NewScanner(os.Stdin); for sc.Scan() { p := strings.Fields(sc.Text()); x, _ := strconv.ParseFloat(p[1], 64); fmt.Printf("%s %s -> [%s]\n", p[0], p[1], fmt.Sprintf(p[0], x)) } }
