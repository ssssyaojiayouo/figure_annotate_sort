# figure_annotate_sort
三国杀时光绘卷拼图自动标注并给出交换步骤。如果没有python环境，更新了拼图还原工具，只需提供截图便可给出可视化的还原步骤


**最后更新**: 2025-09-02 09:48:10

- ✅ 已完成: 第一、二、三、四、五幅图标注
- 🚧 进行中: 第六幅图标注 (预计2025-09-05完成)
- ⏳ 待更新: 第七幅图

## 路径说明
1. reference_patches/fig0x/: 每幅拼图的切片路径，用于精准定位截图碎片位置，目前只有第一幅图，后续会更新。
2. screenshot/fig0x/: 放置未标注的截图，每幅图的截图需要放在相对应的子文件夹下，目前只有第一幅图。
3. output/fig0x/: 标注好的截图输出路径。

## 使用说明
有两种模式，一种是直接给出截图顺序，正确顺序编号为：
<table style="border: none; border-collapse: collapse;">
<tr>
<td align="center">1</td>
<td align="center">2</td>
<td align="center">3</td>
<td align="center">4</td>
</tr>
<tr>
<td align="center">5</td>
<td align="center">6</td>
<td align="center">7</td>
<td align="center">8</td>
</tr>
<tr>
<td align="center">9</td>
<td align="center">10</td>
<td align="center">11</td>
<td align="center">12</td>
</tr>
</table>

另一种是直接给出未排序好的截图，需要注意截图只能包含碎片的部分，如果不裁剪，程序识别率很低很难标注准确。  

截图示意:  
<img src="./screenshot/fig01/test02.jpg" width="500" alt="截图示意">  
 
## 模式1： 直接给出碎片顺序
```python
figure_label = '01'  # 第一幅图参数
screenshot_figure_name = 'test02.jpg'  # 截图图像名
po = [7, 3, 8, 11, 12, 2, 4, 1, 10, 5, 9, 6]  # 直接赋值，不会自动给图像编号
running(figure_label, screenshot_figure_name, po)
```
结果如下：  
<img src="./source/模式1结果.png" width="400" alt="模式1结果">  

## 模式2：给出未标注的截图
```python
figure_label = '01'
screenshot_figure_name = 'test02.jpg'
po = None  # 自动给图像编号，并给出交换步骤
running(figure_label, screenshot_figure_name, po)
```
结果如下：  
<img src="./output/fig01/test02_annotated.jpg" width="500" alt="模式2结果_图像标注">  
<img src="./source/模式2结果.png" width="400" alt="模式2结果_程序运行结果">  

## 拼图还原工具
直接双击exe打开界面如下：  
<img src="./source/exe_fig_1.png" width="500" alt="exe_fig_1">  
只需要拖拽你的裁剪好的截图到指定位置，然后在上方下拉框中选择是第几副图  
<img src="./source/exe_fig_2.png" width="500" alt="exe_fig_2">  
然后点击处理图像，软件自动会根据你的截图得到拼接好的图像，以及交换步骤   
<img src="./source/exe_fig_3.png" width="500" alt="exe_fig_3">  
你点击下一步，软件会提示你哪两个碎片位置变化，对应的旁边的步骤也会高亮  
<img src="./source/exe_fig_4.png" width="500" alt="exe_fig_4">  
最后点完全部步骤，便会完成拼图  
<img src="./source/exe_fig_6.png" width="500" alt="exe_fig_6">  
1. 需要注意的是，exe文件所在的文件夹内必须包含reference_patches文件夹以及里面的每幅图的碎片！！！！
2. exe以及截图的文件路径不能有中文！！！！否则当点击处理图像之后会闪退。

## 联系方式
B站：ssss要加油哦  
闲话：ssss要加油哦  
QQ: 1903425766  

