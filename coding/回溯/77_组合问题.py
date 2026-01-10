"""
给定两个整数 n 和 k，返回 1 ... n 中所有可能的 k 个数的组合。
示例:
输入: n = 4, k = 2
输出: [ [2,4], [3,4], [2,3], [1,2], [1,3], [1,4], ]
"""
# ACM模式
path = []
result = []
def backtracking(n, k, startindex):
    # 终止条件
    if len(path) == k:
        # 收集结果
        result.append(path[:])
        return
    # 处理每个节点
    for i in range(startindex, n + 1):
        path.append(i)
        backtracking(n, k, i+1)
        # 回溯
        path.pop()

def main():
    n, k = map(int, input().split())
    backtracking(n, k, 1)
    for item in result:
        print(item)
if __name__ == "__main__":
    main()
