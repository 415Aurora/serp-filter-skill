"""
给定两个整数 n 和 k，返回 1 ... n 中所有可能的 k 个数的组合。
示例:
输入: n = 4, k = 2
输出: [ [2,4], [3,4], [2,3], [1,2], [1,3], [1,4], ]
"""
# ACM模式 + 剪枝
def backtracking(n, k, startIndex, path, results):
    if len(path) == k:
        results.append(path[:])
        return
    for i in range(startIndex, n-(k-len(path))+1+1):
        path.append(i)
        backtracking(n, k, i+1, path, results)
        path.pop()
def main():
    n, k = map(int, input().split())
    results = []
    backtracking(n, k, 1, [], results)
    for item in results:
        print(item)
if __name__ == "__main__":
    main()

