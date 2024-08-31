#%%
import cv2
import os
import pretty_midi
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from music21 import *
from collections import Counter

        
#* convert mp4 into midi
def mp42midi(upload_folder, filename, processed_folder,write_prg=True):
    color_dict = {0:0} # num: h value in hsv (red)
    instr_dict = {0:pretty_midi.Instrument(0)} # num: Instrument 
    sigma = 0.33  # 0.33 param for Canny   
    file_name_prg = "progress.txt" 
    
    if write_prg:
        with open(file_name_prg, 'w') as file:
            file.write("0")
        
    def get_color(arr,arr_hsv,arr_default):
        arr = arr.astype(int)
        # if max(arr)-min(arr)<30 and max(arr)>250:
        #     color = "w"
        # elif max(arr)-min(arr)<30 and min(arr)<20:
        #     color = "b"
        if max(abs(arr - arr_default))<20:
            return "default"
        else: 
            # print(arr,arr_default)
            # check = [np.amax(abs(var.astype(int) - arr.astype(int)))<30 for var in color_dict.values()]
            check = [abs(int(var) - int(arr_hsv))<25 for var in color_dict.values()]

            if True in set(check): # this color has already appeared
                color = check.index(True)
            else: # new color
                # print("new",color_dict.values())
                if color_dict == {}:
                    i = 0
                else:
                    i = len(color_dict)
                # color_dict[i] = arr
                color_dict[i] = int(arr_hsv)
                instr_dict[i] = pretty_midi.Instrument(i)
                color = i
            return color
    
    def midi_note_from_ctr(min_max_x_y):
        key_incl = [[i,key] for i,key in enumerate(key_loc_all) if key >= min_max_x_y[0] and key <= min_max_x_y[1]] 
        if key_incl == []:
            print("Error: no key is allocated")
            print(min_max_x_y)
            note_number = False
        else:
            white_incl = [key_incl[i][0] for i in range(len(key_incl)) if key_incl[i][1] in white_loc_all]
            if white_incl!=[]: # white key
                # print(f"there is {len(white_incl)} white key included")
                note_number = num_add_lowest + white_incl[0]
            else: # black key
                # print(f"there is {len(key_incl)} black key included")
                note_number = num_add_lowest + key_incl[0][0]
            # print("note_number",note_number)
        return note_number
        

    cap = cv2.VideoCapture(os.path.join(upload_folder, filename))
    if not cap.isOpened():
        print("False")
        return

    # capture info
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    dur = frame_count/fps
    
    if write_prg:
        with open(file_name_prg, 'w') as file:
            file.write("2")
    
    # set bar loc
    loc_keytop = 0
    second_bar = False
    find_capture_moment = False
    for i in range(int(fps*5)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, img = cap.read()
        img_blur = cv2.GaussianBlur(img, (3,3), 0)         # Canny Edge Detection
        med_val = np.median(img_blur)
        min_val = int(max(0, (1.0 - sigma) * med_val))
        max_val = int(max(255, (1.0 + sigma) * med_val))
        edges = cv2.Canny(image=img, threshold1=min_val, threshold2=max_val) # 10,40
        ratio_hline = np.sum(edges==255,axis=1)/width
        loc_hline = np.where(ratio_hline>0.3)[0] # pick hlines detected
        # cv2.imwrite(path + f"edges_{i}.jpg",edges) # edgeは2値関数(0 or 255)の縦×横
        
        contours,hierarchy = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # keep only bar num
        contours = [ctr for ctr in contours if np.max(ctr,axis=0)[0][1]-np.min(ctr,axis=0)[0][1]<40 and np.max(ctr,axis=0)[0][0]<30]
        max_y = [ctr.max(axis=0)[0][1] for ctr in contours]
        loc_keytop = max(loc_keytop,max(max_y))
            
        # 間隔がmax_diff以内の値同士を同じグループとして扱う
        groups = np.split(max_y, np.where(abs(np.diff(max_y)) > 100)[0] + 1)        
        # print(groups)
        
        if i == 0:
            loc_try = max(groups[-1])
        elif find_capture_moment == False:
            if max(groups[-1]) > loc_try: # 動画が動いている
                find_capture_moment = True
                capture_moment = i # frame
                init_bar_loc = loc_keytop
        
        # 真ん中の値が近ければもっとも複雑で大きい形を残す。遠ければ別の数字
        elif find_capture_moment: # 動画が動いている
            if len(groups) > 1 and second_bar == False:            
                yloc_init = max(groups[0])+7
                yloc_last = max(groups[1])+7
                ybar_length = yloc_init - yloc_last
                print(yloc_init,yloc_last)
                
                init_bar = i
                second_bar = True
                
            elif second_bar and abs(init_bar_loc - max(groups[0]))<=1:
                interval_bar_frame = i-capture_moment
                interval_bar_sec = interval_bar_frame/fps # 1つのbar何秒か
                # speed = 60 // (interval_bar_sec / 4) # 60sec / 四分音符一つのsec
                print(interval_bar_frame,interval_bar_sec)
                
                break
            
        if write_prg and i%fps==0:
            with open(file_name_prg, 'w') as file:
                file.write(str(min((2+(i/fps)/3*8),10)))
    
                            
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # capture first part at random moment
    ret, img_default = cap.read()
    
    # capture pure video length, the video ends when all the keys are kept untouched 
    dur_last = int(dur)
    # flag_end = 0
    # cv2.imwrite(path + f"img_default.jpg",img_default[loc_keytop+50:loc_keytop+200]) 
    # for i in np.arange(int(frame_count/10*9),int(frame_count),fps):
    #     cap.set(cv2.CAP_PROP_POS_FRAMES, i) # capture first part at random moment
    #     ret, img = cap.read()
    #     # 大体色が同じ
    #     # print(cv2.subtract(img_default[loc_keytop+50:loc_keytop+200], img[loc_keytop+50:loc_keytop+200]).max())
    #     if cv2.subtract(img_default[loc_keytop+50:loc_keytop+200], img[loc_keytop+50:loc_keytop+200]).max() < 50:
    #         dur_last = i/fps #!
    #         break
    #     cv2.imwrite(path + f"img_{i}.jpg",img[loc_keytop+50:loc_keytop+200]) 
    
    #! dur_last = 2
    
    # 境目の少し左の色を利用
    img_default_grey = cv2.cvtColor(img_default, cv2.COLOR_BGR2GRAY)
    key_line = img_default_grey[loc_keytop+50]
    key_line = np.where(key_line<125,0,1)
    key_line_diff = key_line[1:] - key_line[:-1]
    bound_black_index = np.where(key_line_diff!=0)[0] # 白から黒だけで全ての境目検出できる
    bound_black_drop = np.where(bound_black_index[1:]-bound_black_index[:-1]<5)[0] # 近いものは落とす
    bound_black_index = np.delete(bound_black_index,bound_black_drop+1)
    key_loc_all = (bound_black_index[1:]+bound_black_index[:-1])/2 # keyの真ん中
    key_loc_all = np.insert(key_loc_all,0,bound_black_index[0]/2) # 一番左
    key_loc_all = np.insert(key_loc_all,-1,(len(key_line)+bound_black_index[-1])/2) # 一番右
    key_loc_all = key_loc_all.astype('int')
    key_color_all = key_line[list(key_loc_all)] # keyの色
    key_octave = [1,0,1,0,1,1,0,1,0,1,0,1]
    note_C_all = np.where(np.correlate(key_color_all, key_octave, mode='valid') == np.sum(key_octave))[0]
    num2fitst_C = note_C_all[0] # =3
    oct_lowest = 4-int(len(note_C_all)/2)
    num_add_lowest = oct_lowest*12 - num2fitst_C # number to add for the lowest key in the keyboard to retrieve the note_number
    # print("num_add_lowest",num2fitst_C,oct_lowest,num_add_lowest)
    white_loc_all = key_loc_all[[i for i in range(len(key_loc_all)) if key_octave[(i-num2fitst_C)%12]==1]]
    # black_loc_all = list(set(key_loc_all) - set(white_loc_all))
    
    if write_prg:
        with open(file_name_prg, 'w') as file:
            file.write("10")
    
    #* 確認用
    # if check_key_loc:
    #     for b_x in black_loc_all:
    #         cv2.drawMarker(img_default, position=(b_x, loc_keytop+50), color=(0, 255, 0), \
    #             markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2, line_type=cv2.LINE_4)
    #     for w_x in white_loc_all:
    #         cv2.drawMarker(img_default, position=(w_x, loc_keytop+50), color=(255, 0, 0), \
    #             markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2, line_type=cv2.LINE_4)
    #     if ret:
    #         cv2.imwrite(path + "check_key.jpg", img_default)
    
    # ---------------------------------------------------------------------
            
    # categorize the color and get info
    note_dict = {} # note_number: [color,start,end]
    
    num_bar = dur_last/interval_bar_sec  
    #! num_bar = 5 
    
    # approx_array = np.arange(1,9)/8
    # approx_array = np.append(approx_array,np.arange(1,3)/3) # avoid several 1  
    # approx_array_zero = np.append(approx_array,0)
    
    #* edge detection
    # for i,t in enumerate(np.arange(init_bar+10*interval_bar_frame,init_bar+15*interval_bar_frame,interval_bar_frame)): # t is frame, dur-dur%interval_bar
    for i,t in enumerate(np.arange(init_bar+0*interval_bar_frame,init_bar+num_bar*interval_bar_frame,interval_bar_frame)): # t is frame, dur-dur%interval_bar
        print("execute", i)
        if write_prg:
            with open(file_name_prg, 'w') as file:
                file.write(str(10+(i+1)/num_bar*90))
                
        cap.set(cv2.CAP_PROP_POS_FRAMES, t) 
        ret, img_ori_t = cap.read()
        # cv2.imwrite(path + f"test_{i}.jpg",img_ori_t)
        img = img_ori_t[yloc_last:yloc_init+1]
        arr_hsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        init_time_bar = i*interval_bar_sec
        #* automated thresholds
        img_blur = cv2.GaussianBlur(img, (3,3), 0)         # Canny Edge Detection
        med_val = np.median(img_blur)
        min_val = int(max(0, (1.0 - sigma) * med_val))
        max_val = int(max(255, (1.0 + sigma) * med_val))
        edges = cv2.Canny(image=img, threshold1=min_val, threshold2=max_val) # 80,100
        
        # Display Canny Edge Detection Image
        # cv2.imwrite(path + "edges.jpg",edges) # edgeは2値関数の縦×横
        contours,hierarchy = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        # delete bar number
        contours = [ctr for ctr in contours if np.min(ctr,axis=0)[0][0]>20 or np.max(ctr,axis=0)[0][1]<785]
        # 小さい輪郭は誤検出として削除する
        contours = [ctr for ctr in contours if np.max(ctr,axis=0)[0][0]-np.min(ctr,axis=0)[0][0]>20 and np.max(ctr,axis=0)[0][1]-np.min(ctr,axis=0)[0][1]>10]      
        
        # 鍵盤に近いものが長方形か判定、もやもやなら除外
        # remove_index = []
        # for i,contour in enumerate(contours):
        #     cnt = contour.squeeze(axis=1)
        #     if np.max(cnt[:,1]) - np.min(cnt[:,1]) < ybar_length/10 and yloc_init - np.max(cnt[:,1]) < 10:
        #         # 輪郭を近似する, パラメータが大きいほど粗い判定
        #         epsilon = 0.04 * cv2.arcLength(contour, True)
        #         approx = cv2.approxPolyDP(contour, epsilon, True)
                
        #         # 近似輪郭の頂点数が4つ（長方形）であるかどうかを判定
        #         print(approx)
        #         if len(approx) > 4:
        #             # 長方形でない
        #             remove_index.append(i)  
        # print("remove",remove_index)
        # contours = [cnt for i,cnt in enumerate(contours) if i not in remove_index]
                    
                     
        min_max_x_y_ctr = np.zeros((len(contours),4)) # min x, max x, min y, max y
        for i,contour in enumerate(contours):            
            cnt = contour.squeeze(axis=1)
            # 真ん中より右と左で別に最頻値を利用。もやもやをカウントしないため
            cnt_mid = (np.max(cnt[:,0])+np.min(cnt[:,0]))/2
            count_x_min = Counter([a for a in cnt[:,0] if a < cnt_mid])
            count_x_max = Counter([a for a in cnt[:,0] if a > cnt_mid])
            # left_half_y = [cnt[i,1] for i in range(len(cnt)) if cnt[i,0] < cnt_mid]
            # right_half_y = [cnt[i,1] for i in range(len(cnt)) if cnt[i,0] > cnt_mid]
            # y_max = min(np.max(left_half_y),np.max(right_half_y)) 
            min_max_x_y_ctr[i,0] = count_x_min.most_common()[0][0]
            min_max_x_y_ctr[i,1] = count_x_max.most_common()[0][0]
            min_max_x_y_ctr[i,2] = np.sort(cnt[:,1])[1]
            min_max_x_y_ctr[i,3] = np.sort(cnt[:,1])[::-1][1] # 2番目に小さい値 # 下は線に沿って片側だけ伸びる可能性あり

                    
        ## 全音符の検出
        # print(edges.shape)
        rough_edges = np.where(edges==255,1,0) # まずは01に
        rough_edges = np.where(rough_edges[:,:-2]+rough_edges[:,1:-1]+rough_edges[:,2:]>0,1,0) # 横ブレを大目に見る
        sum_edges = np.sum(rough_edges,axis=0) # (横,)

        long_edges = np.where(sum_edges>edges.shape[0]*0.9,1,0) # (横,) 
        long_edges = np.where(long_edges[1:] - long_edges[:-1]==1,1,0)
        long_edges = np.insert(long_edges,0,1) # 一番左は1として足す
        long_edges[-1] = 1
        long_edges_index_ori = np.where(long_edges)[0]
        a = long_edges_index_ori[1:] - long_edges_index_ori[:-1]
        long_edges_index = long_edges_index_ori[:-1][(a > 15) & (a < 40)]

        # 既に検出されているやつは除く      
        min_x_int = min_max_x_y_ctr[:,0].astype(int)
        set_detected = set(min_x_int)|set(min_x_int-1)|set(min_x_int-2)
        long_edges_left = np.setdiff1d(long_edges_index, np.array(list(set_detected)))

        # 対応する右側を取得
        long_edges_right = np.zeros_like(long_edges_left)
        for i,left in enumerate(long_edges_left):
            left_index = np.nonzero(long_edges_index_ori == left)[0][0]
            long_edges_right[i] = long_edges_index_ori[left_index+1]    
        # 真ん中の色をもとの色と比較し、変化してるもののみ残す
        drop_index = []
        for i,left in enumerate(long_edges_left):
            if cv2.subtract(img_ori_t[int((yloc_init+yloc_last)/2),int((long_edges_right[i]+left)/2)], img_default[int((yloc_init+yloc_last)/2),int((long_edges_right[i]+left)/2)]).max() < 30:
                drop_index.append(i)
        # print(drop_index)
        long_edges_left = np.delete(long_edges_left,drop_index)
        long_edges_right = np.delete(long_edges_right,drop_index)

        # 4つ角の点をcontoursに足す、5でスタート位置調整
        insert_arr = np.array([long_edges_left,long_edges_right,[yloc_last]*len(long_edges_right),[yloc_init]*len(long_edges_right)])
        min_max_x_y_ctr = np.concatenate([min_max_x_y_ctr, insert_arr.T])
        for i in range(len(long_edges_left)):
            insert_arr = np.array([[[long_edges_left[i],yloc_last]],[[long_edges_left[i],yloc_init]],[[long_edges_right[i],yloc_init]],[[long_edges_right[i],yloc_last]]])
            contours.append(insert_arr)
            
        #* 確認用
        # fig, ax = plt.subplots(figsize=(16, 8))
        # ax.imshow(img)
        # ax.set_axis_off()
        # for i, cnt in enumerate(contours):
        #     # 形状を変更する。(NumPoints, 1, 2) -> (NumPoints, 2)
        #     cnt = cnt.squeeze(axis=1)
        #     # 輪郭の点同士を結ぶ線を描画する。
        #     ax.add_patch(plt.Polygon(cnt, color="b", fill=None, lw=2))
        #     # 輪郭の点を描画する。
        #     ax.plot(cnt[:, 0], cnt[:, 1], "ro", mew=0, ms=4)
        #     # 輪郭の番号を描画する。
        #     ax.text(cnt[0][0], cnt[0][1], i, color="r", size="10", bbox=dict(fc="w")) 
        
        # fig, ax = plt.subplots(figsize=(16, 8))
        # ax.imshow(img)
        # ax.set_axis_off()
        # for i, min_max_x_y in enumerate(min_max_x_y_ctr):
        #     x_min,x_max,y_min,y_max = min_max_x_y
        #     # Create a rectangle patch
        #     rect = patches.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
        #                             linewidth=2, edgecolor='r', facecolor='none')
        #     # Add the rectangle to the plot
        #     ax.add_patch(rect)
            
        # ----------------------------------------------------------
            
        for i,ctr in enumerate(min_max_x_y_ctr): # []
            ave_x = int((ctr[0] + ctr[1])/2)
            ave_y = int((ctr[2] + ctr[3])/2)
            color = get_color(img[ave_y][ave_x],arr_hsv[ave_y,ave_x,(0)],img_default[ave_y][ave_x])
            if color!="default":
                note_number = midi_note_from_ctr(ctr)
                if note_number: # not False
                
                    # 近似
                    start_time = (yloc_init-ctr[3])/ybar_length
                    end_time = (yloc_init-ctr[2])/ybar_length
                    # length = (min_max_x_y_ctr[i][3] - min_max_x_y_ctr[i][2])/ybar_length
                    # print(i,start_time, end_time, length)
                    # diff = np.abs(start_time - approx_array_zero) 
                    #* avoid 
                    # if np.min(diff) < 0.03:
                    #     start_time = approx_array_zero[np.argmin(diff)]
                    
                    # if length < 1/8 -0.03: # 細かく近似？
                    #     # print("small", length)
                    #     pass
                    # else:
                    #     diff = np.abs(length - approx_array) 
                    #     if np.min(diff) < 0.03:
                    #         length = approx_array[np.argmin(diff)] 
                    #         # print(length)   
                            
                    start_time *= interval_bar_sec
                    end_time *= interval_bar_sec
                            
                    note_add = pretty_midi.Note(velocity=80, pitch=note_number, \
                        start=init_time_bar + start_time, \
                        end=init_time_bar + end_time)
                    instr = instr_dict[color]
                    instr.notes.append(note_add) #! instrument           
            
                             
    # create midi file
    midi_file = pretty_midi.PrettyMIDI(initial_tempo=100.0) # whole instruments
    # piano = pretty_midi.Instrument("piano")  
    for instr in instr_dict.values():
        midi_file.instruments.append(instr)
    
    # note = pretty_midi.Note(velocity=100, pitch=30, start=0, end=0.5)
    # instr = pretty_midi.Instrument(0)
    # instr.notes.append(note) 
    # midi_file.instruments.append(instr)
    
    # write out midi
    # ファイル名から拡張子を取り除く
    file_name_without_ext = os.path.splitext(filename)[0]
    # 元のディレクトリ名と拡張子なしのファイル名を結合
    file_without_ext = os.path.join(processed_folder, file_name_without_ext)
    midi_file.write(file_without_ext+".midi")
    
# if __name__ == "__main__":  
    # check_key_loc = True
    # file_path = "C:\\Users\\kanae\\Documents\\MEGAsync Uploads\\Edit_score\\synthesia\\Wataridori\\ワタリドリ.mp4" # ghost\\
    # mp42midi(file_path)


#%%
#! 課題：音の若干のずれ、小節のつなぎ目
#! 次は他の曲もやってみる

# 小節は数字が見えたら区切る、線はないことも多い
# 背景がdetectされちゃう
#! オクターブの判定
# 速度
#! ２つくっついてるのがまとめて一つになっちゃう
#! 音がたまにダブっちゃう（ワタリドリ10-15）
