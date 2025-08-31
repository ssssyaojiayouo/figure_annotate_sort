import sys
import os
import cv2
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QGroupBox, QGridLayout,
                             QMessageBox, QComboBox, QSpinBox, QProgressBar,
                             QListWidget, QListWidgetItem)
from PyQt5.QtGui import (QPixmap, QFont, QPainter, QPen, QColor,  QBrush)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer


class ImageProcessingThread(QThread):
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(list, list, list, list)

    def __init__(self, screenshot_path, ref_dir, threshold):
        super().__init__()
        self.screenshot_path = screenshot_path
        self.ref_dir = ref_dir
        self.threshold = threshold

    def run(self):
        try:
            screenshot_area = cv2.imread(self.screenshot_path)
            if screenshot_area is None:
                raise ValueError("无法加载截图图像")

            ref_files = sorted([f for f in os.listdir(self.ref_dir) if f.endswith('.png')],
                               key=self.natural_sort_key)
            ref_pieces = []
            ref_paths = []
            for i, ref_file in enumerate(ref_files):
                ref_path = os.path.join(self.ref_dir, ref_file)
                ref_img = cv2.imread(ref_path)
                if ref_img is None:
                    raise ValueError(f"无法加载参考碎片: {ref_file}")
                ref_pieces.append(ref_img)
                ref_paths.append(ref_path)
                self.progress_signal.emit(int((i + 1) / len(ref_files) * 30))

            screenshot_gray = self.preprocess_image(screenshot_area)
            matches = {}

            for ref_idx, ref_piece in enumerate(ref_pieces):
                ref_gray = self.preprocess_image(ref_piece)
                h, w = screenshot_gray.shape[:2]
                ref_resized = cv2.resize(ref_gray, (w // 4, h // 3))

                result = cv2.matchTemplate(screenshot_gray, ref_resized, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                if max_val >= self.threshold:
                    center_x = max_loc[0] + ref_resized.shape[1] // 2
                    center_y = max_loc[1] + ref_resized.shape[0] // 2
                    matches[(center_x, center_y)] = ref_idx + 1

                self.progress_signal.emit(30 + int((ref_idx + 1) / len(ref_pieces) * 60))

            piece_order = self.get_piece_order(screenshot_area, matches)
            swaps, _ = self.min_swap_sort(piece_order)
            piece_height, piece_width = ref_pieces[0].shape[:2]

            self.result_signal.emit(piece_order, swaps, ref_paths, [piece_width, piece_height])

        except Exception as e:
            self.result_signal.emit([], [], [], str(e))

    def natural_sort_key(self, s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

    def preprocess_image(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        return gray

    def get_piece_order(self, screenshot_area, matches):
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

    def min_swap_sort(self, arr):
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
        return swaps, result_arr


class PuzzleSorterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("拼图碎片排序工具(By: ssss要加油哦)(B站闲话同名)")
        self.setGeometry(100, 100, 1100, 750)
        self.initUI()

        self.screenshot_path = ""
        self.ref_dir = ""
        self.piece_order = []
        self.swaps = []
        self.current_step = 0
        self.current_order = []
        self.original_image = None
        self.stitched_image = None
        self.ref_pieces = []  # 存储所有碎片的QPixmap
        self.piece_size = [0, 0]  # 碎片宽度和高度
        self.drag_pos = None
        self.highlighted_pieces = []  # 存储高亮碎片索引

    def initUI(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        title_label = QLabel("拼图碎片排序工具")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        input_group = QGroupBox("输入设置")
        input_layout = QGridLayout()

        self.screenshot_label = QLabel("未选择截图")
        self.screenshot_label.setAcceptDrops(True)
        self.screenshot_label.dragEnterEvent = self.dragEnterEvent
        self.screenshot_label.dropEvent = self.dropEvent
        screenshot_btn = QPushButton("选择截图")
        screenshot_btn.clicked.connect(self.select_screenshot)

        self.puzzle_number_label = QLabel("选择拼图:")
        self.puzzle_number_combo = QComboBox()

        puzzle_options = [
            "第1幅图-樱花漫舞",
            "第2幅图-雪后初晴",
            "第3幅图-柿柿如意",
            "第4幅图-稻谷飘香",
            "第5幅图-春日琴韵",
            "第6幅图-雨中嬉戏",
            "第7幅图-暖室茶香"
        ]
        self.puzzle_number_combo.addItems(puzzle_options)
        self.puzzle_number_combo.currentIndexChanged.connect(self.update_ref_dir)

        self.threshold_label = QLabel("匹配阈值:")
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(40, 90)
        self.threshold_spin.setValue(60)
        self.threshold_spin.setSuffix("%")

        input_layout.addWidget(QLabel("拼图截图:"), 0, 0)
        input_layout.addWidget(self.screenshot_label, 0, 1)
        input_layout.addWidget(screenshot_btn, 0, 2)

        input_layout.addWidget(self.puzzle_number_label, 1, 0)
        input_layout.addWidget(self.puzzle_number_combo, 1, 1)

        input_layout.addWidget(self.threshold_label, 2, 0)
        input_layout.addWidget(self.threshold_spin, 2, 1)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        process_btn = QPushButton("处理图像")
        process_btn.clicked.connect(self.process_image)
        process_btn.setFont(QFont("Arial", 12))
        main_layout.addWidget(process_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        result_group = QGroupBox("结果")
        result_layout = QHBoxLayout()
        result_layout.setStretch(0, 2)
        result_layout.setStretch(1, 2)

        image_group = QGroupBox("图像预览")
        image_layout = QVBoxLayout()

        self.original_image_label = QLabel()
        self.original_image_label.setAlignment(Qt.AlignCenter)
        self.original_image_label.setMinimumSize(380, 250)
        self.original_image_label.setText("原始截图将显示在这里(可以直接把截图拖到这个地方)")
        self.original_image_label.setAcceptDrops(True)
        self.original_image_label.dragEnterEvent = self.dragEnterEvent
        self.original_image_label.dropEvent = self.dropEvent

        self.stitched_image_label = QLabel()
        self.stitched_image_label.setAlignment(Qt.AlignCenter)
        self.stitched_image_label.setMinimumSize(380, 250)
        self.stitched_image_label.setText("拼接后的图像将显示在这里")
        self.stitched_image_label.setMouseTracking(True)
        self.stitched_image_label.mousePressEvent = self.mousePressEvent
        self.stitched_image_label.mouseMoveEvent = self.mouseMoveEvent
        self.stitched_image_label.mouseReleaseEvent = self.mouseReleaseEvent

        image_layout.addWidget(QLabel("原始截像:"))
        image_layout.addWidget(self.original_image_label)
        image_layout.addWidget(QLabel("拼接图像:"))
        image_layout.addWidget(self.stitched_image_label)
        image_group.setLayout(image_layout)

        text_group = QGroupBox("排序结果")
        text_layout = QVBoxLayout()
        text_group.setFixedWidth(400)

        self.piece_order_label = QLabel("碎片顺序: ")
        self.piece_order_label.setFont(QFont("Arial", 10))

        self.steps_list = QListWidget()
        self.steps_list.setFont(QFont("Arial", 10))
        self.steps_list.setMinimumHeight(100)
        self.steps_list.setMinimumWidth(380)

        steps_label = QLabel("交换步骤:")
        steps_label.setFont(QFont("Arial", 10))

        self.swap_count_label = QLabel("总交换次数: 0")
        self.swap_count_label.setFont(QFont("Arial", 10, QFont.Bold))

        self.next_step_btn = QPushButton("下一步")
        self.next_step_btn.clicked.connect(self.next_step)
        self.next_step_btn.setEnabled(False)

        text_layout.addWidget(self.piece_order_label)
        text_layout.addWidget(steps_label)
        text_layout.addWidget(self.steps_list)
        text_layout.addWidget(self.swap_count_label)
        text_layout.addWidget(self.next_step_btn)
        text_group.setLayout(text_layout)

        result_layout.addWidget(image_group)
        result_layout.addWidget(text_group)
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)

        button_layout = QHBoxLayout()
        save_result_btn = QPushButton("保存结果")
        save_result_btn.clicked.connect(self.save_results)
        save_image_btn = QPushButton("保存图片")
        save_image_btn.clicked.connect(self.save_image)
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset)
        exit_btn = QPushButton("退出")
        exit_btn.clicked.connect(self.close)

        button_layout.addWidget(save_result_btn)
        button_layout.addWidget(save_image_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(exit_btn)
        main_layout.addLayout(button_layout)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.screenshot_path = file_path
                self.screenshot_label.setText(os.path.basename(file_path))
                self.display_image(file_path, self.original_image_label)
                break

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and hasattr(self, 'stitched_image') and self.stitched_image:
            self.drag_pos = event.pos()
            self.stitched_image_label.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_pos:
            pass

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = None
            self.stitched_image_label.setCursor(Qt.ArrowCursor)

    def update_ref_dir(self):
        puzzle_index = self.puzzle_number_combo.currentIndex() + 1
        base_dir = os.getcwd()
        self.ref_dir = os.path.join(base_dir, f"reference_patches/fig{str(puzzle_index).zfill(2)}")
        if not os.path.exists(self.ref_dir):
            os.makedirs(self.ref_dir, exist_ok=True)

    def select_screenshot(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择拼图截图", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.screenshot_path = path
            self.screenshot_label.setText(os.path.basename(path))
            self.display_image(path, self.original_image_label)

    def display_image(self, path, label):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.original_image = pixmap.copy()
            pixmap = pixmap.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap)
        else:
            label.setText("无法加载图像")

    def process_image(self):
        if not self.screenshot_path:
            QMessageBox.warning(self, "警告", "请先选择拼图截图")
            return

        self.update_ref_dir()
        if not os.path.exists(self.ref_dir) or not os.listdir(self.ref_dir):
            QMessageBox.warning(self, "警告", f"参考碎片目录不存在或为空: {self.ref_dir}")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        threshold = self.threshold_spin.value() / 100.0

        self.worker = ImageProcessingThread(
            self.screenshot_path,
            self.ref_dir,
            threshold
        )
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.result_signal.connect(self.handle_results)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def handle_results(self, piece_order, swaps, ref_paths, piece_size):
        self.progress_bar.setVisible(False)

        if not piece_order:
            QMessageBox.critical(self, "错误", ref_paths)
            return

        self.piece_order = piece_order
        self.swaps = swaps
        self.current_order = piece_order.copy()
        self.current_step = 0
        self.piece_size = piece_size
        self.highlighted_pieces = []

        self.ref_pieces = []
        for path in ref_paths:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(piece_size[0], piece_size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.ref_pieces.append(pixmap)

        self.create_stitched_image()
        if self.stitched_image:
            pixmap = self.stitched_image.scaled(
                self.stitched_image_label.width(),
                self.stitched_image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.stitched_image_label.setPixmap(pixmap)

        self.piece_order_label.setText(f"碎片顺序: {piece_order}")

        self.steps_list.clear()
        for step, (idx1, idx2) in enumerate(swaps, 1):
            item = QListWidgetItem(f"步骤 {step}: 交换位置 {idx1 + 1} 和 {idx2 + 1}")
            item.setData(Qt.UserRole, (idx1, idx2))
            self.steps_list.addItem(item)

        self.swap_count_label.setText(f"总交换次数: {len(swaps)}")
        self.next_step_btn.setEnabled(len(swaps) > 0)

    def create_stitched_image(self):
        if not self.ref_pieces or len(self.ref_pieces) < 12:
            return

        width = self.piece_size[0] * 4
        height = self.piece_size[1] * 3
        stitched_image = QPixmap(width, height)
        stitched_image.fill(Qt.transparent)

        painter = QPainter(stitched_image)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        for i, piece_idx in enumerate(self.current_order):
            if piece_idx < 1 or piece_idx > len(self.ref_pieces):
                continue

            row = i // 4
            col = i % 4
            x = col * self.piece_size[0]
            y = row * self.piece_size[1]

            painter.drawPixmap(x, y, self.ref_pieces[piece_idx - 1])

            if i in self.highlighted_pieces:
                highlight_color = QColor(255, 0, 0, 180)
                painter.setBrush(QBrush(highlight_color))
                painter.drawRect(x, y, self.piece_size[0], self.piece_size[1])
                pen = QPen(QColor(255, 0, 0))
                pen.setWidth(3)
                painter.setPen(pen)
                painter.drawRect(x, y, self.piece_size[0], self.piece_size[1])

        painter.end()
        self.stitched_image = stitched_image

    def next_step(self):
        if self.current_step < len(self.swaps):
            idx1, idx2 = self.swaps[self.current_step]
            self.highlighted_pieces = [idx1, idx2]
            self.current_order[idx1], self.current_order[idx2] = self.current_order[idx2], self.current_order[idx1]
            self.create_stitched_image()
            if self.stitched_image:
                pixmap = self.stitched_image.scaled(
                    self.stitched_image_label.width(),
                    self.stitched_image_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.stitched_image_label.setPixmap(pixmap)

            self.current_step += 1
            self.piece_order_label.setText(f"当前碎片顺序: {self.current_order}")
            self.swap_count_label.setText(f"已完成交换: {self.current_step}/{len(self.swaps)}")
            self.highlight_current_step()

            if self.current_step >= len(self.swaps):
                self.next_step_btn.setEnabled(False)
                QMessageBox.information(self, "完成", "所有交换步骤已完成！")
            QTimer.singleShot(1000, self.clear_highlight)

    def highlight_current_step(self):
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            item.setBackground(Qt.transparent)

        if self.current_step > 0 and self.current_step - 1 < self.steps_list.count():
            current_step_item = self.steps_list.item(self.current_step - 1)

            highlight_color = QColor(255, 200, 200, 200)
            current_step_item.setBackground(highlight_color)

            self.steps_list.scrollToItem(current_step_item)

    def clear_highlight(self):
        self.highlighted_pieces = []
        self.create_stitched_image()

        if self.stitched_image:
            pixmap = self.stitched_image.scaled(
                self.stitched_image_label.width(),
                self.stitched_image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.stitched_image_label.setPixmap(pixmap)

        self.highlight_current_step()

    def save_results(self):
        if not hasattr(self, 'piece_order') or not self.piece_order:
            QMessageBox.warning(self, "警告", "没有可保存的结果")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "文本文件 (*.txt);;所有文件 (*)", options=options
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("拼图碎片排序结果\n")
                    f.write("=" * 30 + "\n\n")
                    f.write(f"原始图像: {os.path.basename(self.screenshot_path)}\n")
                    f.write(f"参考碎片目录: {os.path.basename(self.ref_dir)}\n")
                    f.write(f"匹配阈值: {self.threshold_spin.value()}%\n\n")
                    f.write(f"初始碎片顺序: {self.piece_order}\n")
                    f.write(f"当前碎片顺序: {self.current_order}\n\n")
                    f.write("交换步骤:\n")
                    for step, (idx1, idx2) in enumerate(self.swaps, 1):
                        f.write(f"步骤 {step}: 交换位置 {idx1 + 1} 和 {idx2 + 1}\n")
                    f.write(f"\n总交换次数: {len(self.swaps)}\n")
                    f.write(f"已完成交换: {self.current_step}\n")

                QMessageBox.information(self, "成功", "结果已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def save_image(self):
        if not hasattr(self, 'stitched_image') or not self.stitched_image:
            QMessageBox.warning(self, "警告", "没有可保存的图像")
            return

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", "PNG图像 (*.png);;JPEG图像 (*.jpg *.jpeg);;所有文件 (*)", options=options
        )

        if file_path:
            try:
                self.stitched_image.save(file_path)
                QMessageBox.information(self, "成功", "图像已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def reset(self):
        self.screenshot_path = ""
        self.ref_dir = ""
        self.screenshot_label.setText("未选择截图")
        self.original_image_label.clear()
        self.stitched_image_label.clear()
        self.piece_order_label.setText("碎片顺序: ")

        self.steps_list.clear()
        self.swap_count_label.setText("总交换次数: 0")
        self.threshold_spin.setValue(60)
        self.progress_bar.setVisible(False)
        self.current_step = 0
        self.current_order = []
        self.stitched_image = None
        self.original_image = None
        self.ref_pieces = []
        self.piece_size = [0, 0]
        self.next_step_btn.setEnabled(False)
        self.puzzle_number_combo.setCurrentIndex(0)
        self.highlighted_pieces = []


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PuzzleSorterApp()
    window.show()
    sys.exit(app.exec_())
