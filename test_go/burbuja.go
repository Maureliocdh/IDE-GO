package main
import "fmt"

// BubbleSort ordena un arreglo de enteros
func BubbleSort(arr []int) []int {
    n := len(arr)
    for i := 0; i < n; i++ {
        for j := 0; j < n-i-1; j++ {
            // Compara adyacentes y los intercambia si están desordenados
            if arr[j] > arr[j+1] {
                arr[j], arr[j+1] = arr[j+1], arr[j]
            }
        }
    }
    return arr
}

func main() {
    datos := []int{64, 34, 25, 12, 22, 11, 90}
    fmt.Println("Original:", datos)
    BubbleSort(datos)
    fmt.Println("Ordenado:", datos)
}





