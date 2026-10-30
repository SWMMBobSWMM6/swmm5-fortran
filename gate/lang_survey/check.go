// check.go: Go's own math package against glibc's results in vec.txt
package main

import (
	"bufio"
	"fmt"
	"math"
	"os"
	"strconv"
	"strings"
)

func main() {
	f, _ := os.Open(os.Args[1])
	sc := bufio.NewScanner(f)
	bad, n := map[string]int{}, map[string]int{}
	order := []string{"pow", "exp", "log", "log10", "sin", "cos"}
	for sc.Scan() {
		p := strings.Fields(sc.Text())
		xb, _ := strconv.ParseUint(p[1], 16, 64)
		yb, _ := strconv.ParseUint(p[2], 16, 64)
		rb, _ := strconv.ParseUint(p[3], 16, 64)
		x, y := math.Float64frombits(xb), math.Float64frombits(yb)
		var r float64
		switch p[0] {
		case "pow":
			r = math.Pow(x, y)
		case "exp":
			r = math.Exp(x)
		case "log":
			r = math.Log(x)
		case "log10":
			r = math.Log10(x)
		case "sin":
			r = math.Sin(x)
		case "cos":
			r = math.Cos(x)
		}
		n[p[0]]++
		if math.Float64bits(r) != rb {
			bad[p[0]]++
		}
	}
	for _, k := range order {
		fmt.Printf("%-6s %7d of %d differ\n", k, bad[k], n[k])
	}
}
