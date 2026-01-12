# 在这里写上你的代码 :-)
"""
找出所有相加之和为n的k个数的组合。组合中只允许含有1-9的正整数，并且每种组合中不存在重复的数字。

说明：
所有数字都是正整数。
解集不能包含重复的组合。
示例 1: 输入: k = 3, n = 7 输出: [[1,2,4]]
示例 2: 输入: k = 3, n = 9 输出: [[1,2,6], [1,3,5], [2,3,4]]
"""
# 剪枝
def backtracking(n, k, curSum, startIndex, path, results):
    if len(path) == k:
        if curSum == n:
            results.append(path[:])
        return
    for i in range(startIndex, 9-(k-len(path))+2):
        curSum += i
        if curSum > n:
            return
        path.append(i)
        backtracking(n, k, curSum, i+1, path, results)
        # 回溯过程！！
        # 和减小、弹出节点
        curSum -= i
        path.pop()
def main():
    k, n = map(int, input().split())
    results = []
    backtracking(n, k, 0, 1, [], results)
    for item in results:
        print(item)
if __name__ == "__main__":
    main()
