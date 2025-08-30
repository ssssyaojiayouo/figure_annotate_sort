# coding=utf-8
# @Author    : ssss要加油哦
import cv2
import numpy as np
import os
import glob
import re


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return gray


def find_pieces_with_improved_matching(screenshot_area, ref_pieces, threshold=0.6):
    matches = {}
    screenshot_gray = preprocess_image(screenshot_area)
    for ref_idx, ref_piece in enumerate(ref_pieces):
        ref_gray = preprocess_image(ref_piece)
        h, w = screenshot_gray.shape[:2]
        ref_resized = cv2.resize(ref_gray, (w // 4, h // 3))
        methods = [cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED]

        best_match_val = 0
        best_match_loc = None

        for method in methods:
            result = cv2.matchTemplate(screenshot_gray, ref_resized, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val > best_match_val:
                best_match_val = max_val
                best_match_loc = max_loc
        if best_match_val >= threshold:
            center_x = best_match_loc[0] + ref_resized.shape[1] // 2
            center_y = best_match_loc[1] + ref_resized.shape[0] // 2
            matches[(center_x, center_y)] = ref_idx + 1
        else:
            print(f"未找到碎片 {ref_idx + 1}, 最高匹配度: {best_match_val:.2f}")

    return matches


def annotate_screenshot_directly(screenshot_area_path, ref_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    screenshot_area = cv2.imread(screenshot_area_path)
    ref_files = sorted(glob.glob(os.path.join(ref_dir, "*.png")), key=natural_sort_key)

    ref_pieces = []
    for ref_path in ref_files:
        ref_img = cv2.imread(ref_path)
        ref_pieces.append(ref_img)
    best_matches = {}

    for threshold in np.arange(0.4, 0.8, 0.05):
        matches = find_pieces_with_improved_matching(screenshot_area, ref_pieces, threshold)

        if len(matches) > len(best_matches):
            best_matches = matches

    piece_order = get_piece_order(screenshot_area, best_matches)

    # 标注数字
    annotated_img = screenshot_area.copy()
    for (x, y), number in best_matches.items():
        cv2.putText(annotated_img,
                    str(number),
                    (x - 10, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.8,
                    (0, 0, 255),
                    8,
                    cv2.LINE_AA)

    screenshot_filename = os.path.basename(screenshot_area_path)
    name, ext = os.path.splitext(screenshot_filename)
    output_path = os.path.join(output_dir, f"{name}_annotated{ext}")
    cv2.imwrite(output_path, annotated_img)
    print(f"标注完成！找到 {len(best_matches)} 个碎片，保存至: {output_path}")
    return piece_order


def get_piece_order(screenshot_area, matches):
    h, w = screenshot_area.shape[:2]
    block_h = h // 3
    block_w = w // 4
    grid = [[0 for _ in range(4)] for _ in range(3)]
    for (x, y), number in matches.items():
        row = y // block_h
        col = x // block_w
        if 0 <= row < 3 and 0 <= col < 4:
            grid[row][col] = number

    piece_order = []
    for row in grid:
        for number in row:
            piece_order.append(number)
    return piece_order


def min_swap_sort(arr):
    n = len(arr)
    sorted_arr = sorted(arr)
    pos_map = {}
    for idx, val in enumerate(sorted_arr):
        pos_map[val] = idx
    target = [pos_map[x] for x in arr]

    visited = [False] * n
    cycles = []

    for i in range(n):
        if not visited[i]:
            cycle = []
            cur = i
            while not visited[cur]:
                visited[cur] = True
                cycle.append(cur)
                cur = target[cur]
            cycles.append(cycle)

    swaps = []
    result_arr = arr.copy()
    for cycle in cycles:
        if len(cycle) <= 1:
            continue

        for j in range(1, len(cycle)):
            idx1, idx2 = cycle[0], cycle[j]
            result_arr[idx1], result_arr[idx2] = result_arr[idx2], result_arr[idx1]
            swaps.append((idx1, idx2))
    return swaps, arr



def running(figure_label, screenshot_figure_name, po=None):
    if po is not None:
        print("\n原始数组:", po)
        swaps, sorted_data = min_swap_sort(po)
        print("\n交换步骤:")
        for step, (idx1, idx2) in enumerate(swaps, 1):
            print(f"步骤 {step}: 交换位置 {idx1 + 1} 和 {idx2 + 1}")
        print("\n总交换次数:", len(swaps))
    else:
        # 标注数字
        piece_order = annotate_screenshot_directly(
            screenshot_area_path=f'screenshot/fig{figure_label}/{screenshot_figure_name}',
            ref_dir=f'reference_patches/fig{figure_label}/',
            output_dir=f'output/fig{figure_label}/',
        )

        # 交换排序
        print("\n原始数组:", piece_order)
        swaps, sorted_data = min_swap_sort(piece_order)
        print("\n交换步骤:")
        for step, (idx1, idx2) in enumerate(swaps, 1):
            print(f"步骤 {step}: 交换位置 {idx1 + 1} 和 {idx2 + 1}")
        print("\n总交换次数:", len(swaps))
    return 0


if __name__ == '__main__':
    figure_label = '02'
    screenshot_figure_name = 'test01.jpg'
    po = None  # 自动给图像编号，并给出交换步骤
    running(figure_label, screenshot_figure_name, po)

