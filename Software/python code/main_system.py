from module import *

num_assemble   =   5                            # 합치고자 하는 이미지의 수
delay_time     =   7                            # 모터가 구동하고 이미지를 저장하기 전까지 주는 delay

img_width      =   3840                         # 이미지는 4K로 처리
img_height     =   2160
roi_y          =   1500                         # 다섯 번째 이미지는 1500 픽셀 y값 까지 roi를 설정

arduino        = serial.Serial(port = 'COM4', baudrate = 9600)      # serial 통신을 위한 baudrate는 9600으로 설정

# variable definition
# - capture flag : 이미지를 저장할지에 대한 여부
# - img captured : 이미지를 저장했는지에 대한 여부
capture_flag = False                            # thread 간의 변수 호환을 위한 전역 변수 
img_captured = False                            # thread 간의 변수 호환을 위한 전역 변수 

class communicate :

    def __init__(self) :
        
        self.motor_loc  =  0                    # send flag (python - arduino)    : 모터 위치 정렬 정보
        self.motor_rot  =  False                # recieve flag (arduino - python) : 모터 구동 여부 정보

    def send_to_arduino(self) :
    
        arduino.write(f"{self.motor_loc}\n".encode())       # motor가 이동할 위치를 MCU로 전송
    
    def recv_from_arduino(self) :               
        
        self.motor_rot = int(arduino.readline())            # motor의 구동 여부를 MCU에서 수신
        
        
class control(communicate) :                    # 통신 class를 모터 구동 class에 상속
    
    def __init__(self) :
        
        super().__init__()
        
    def move_motor(self) :
        
        global capture_flag, img_captured       # thread 간의 변수 동기화를 위해 두 flag를 전역 변수로 설정
        
        if not self.motor_rot :                 # 모터가 구동중이지 않다면
            
            capture_flag = True                 # 프레임 캡쳐 flag를 True로 설정
            
            img_captured = False                # 프레임 캡쳐 완료 flag를 False로 설정
            
            self.state_update()                 # 모터를 다음 위치로 이동시키기 위해 state 업데이트

            self.send_to_arduino()              # 모터를 다음 위치로 이동

            self.motor_rot     =  True          # 모터의 현재 구동 상태 업데이트 : True --> False

            time.sleep(delay_time)              # 모터 안정화까지 대기

            self.motor_rot     =  False         # 모터의 현재 구동 상태 업데이트 : False --> True
    
    
    def state_update(self) :
        
        self.motor_loc += 1

        if self.motor_loc == num_assemble : self.motor_loc = 0     # state가 5이되면 초기 위치로 정렬
        

class webcam(control) :                         # 모터 구동 class를 webcam class에 종속
    
    def __init__(self) :
        
        super().__init__()
        
        self.cap  =  cv.VideoCapture(cv.CAP_DSHOW + 1)      # 연결된 USB 카메라를 연결
        
        self.cap.set(cv.CAP_PROP_AUTOFOCUS, 0.15)
        
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH , img_width)   # 4K 해상도 설정
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, img_height)
        
        self.ret, self.frame  =  None, None                 
        
        self.org_img_list     =  []                         # 각 stage의 원본 이미지를 저장할 리스트
        self.eval_img_list    =  []                         # 각 stage의 평가된 이미지를 저장할 리스트
        
        self.terminate        =  False                      # 웹캠 thread를 종료할 조건 변수
        self.print_cnt        =  0
    
    
    def capture_img(self) :
        
        while not self.terminate :                          # 카메라 종료조건이 아닌 경우
            
            self.ret, self.frame = self.cap.read()          # 현재 카메라의 프레임을 받아옴
            
            if self.ret :
                
                self.get_img()                              # 모터가 몸추고, 이미지를 캡쳐해야 하는 타이밍에 이미지를 얻는 함수
                                
                cv.imshow('org frame', cv.resize(self.frame, dsize = (640, 480)))   # 보여주는 이미지는 해상도를 낮춰서 보여줌
                
            cv.waitKey(1)
     
        
    def get_img(self) :
        
        global capture_flag, img_captured                   
        
        if capture_flag and not img_captured :              # 이미지를 한 번만 저장하기 위한 조건 변수들
            
            
            if len (self.org_img_list) == 4  :  self.org_img_list.append(self.frame[0 : roi_y, 0 : 3840])      # 다섯 번째는 잘라서 저장      
            
            else  :  self.org_img_list.append(self.frame)                            # 현재 스테이트의 프레임을 리스트에 저장
                
            # 아래 세줄 : 각 위치에서의 개별 이미지를 저장하고 싶다면 주석해제 (optional)    
            
            # timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")      # 파일명은 현재 시간을 기준으로 저장

            # filename = f"./image_evaluation/{timestamp}.png" 

            # cv.imwrite(filename, self.frame)                                        # 이미지를 정해진 경로에 저장
                        
            capture_flag = False                            # 저장 완료후에는 각 flag들을 초기화
            
            img_captured = True
            
    
    def evaluate_sample(self) :                             # 저장된 이미지에 대해 품질 평가를 진행하는 함수
        
        pixel_size              =   12                      # 픽셀 사이즈   : 12로 설정
        grid_size               =   60                      # 그리드 사이즈 : 최종 이미지에서 그리드를 그리기 위한 격자 크기 (optional)
        diff_threshold          =   7.5                     # 픽셀 intensity 차이로 결함을 감지하기 위한 threshold
        
        
        weights = {1: 10, 2: 20, 3: 40, 4: 20, 5: 10}       # 각 샘플의 그레이드를 매기기 위한 변수들
        overall_score = 100
        dcount = 0

        for img in self.org_img_list :                      # 리스트에 저장된 이미지를 기반으로 하나씩 처리
            
            img_height, img_width, _ = img.shape            # 각 이미지 별로 img의 크기, 너비를 얻어온다 (마지막 이미지는 크기가 다르기 때문에 필요)
            
            gray_values = []                                
            
            gray_img    = cv.cvtColor(img, cv.COLOR_BGR2GRAY)   # 먼저, 이미지에 대해 grayscale로 변환
            
            blurred_img = cv.GaussianBlur(gray_img, (5,5), 0)   # 그 후, 노이즈 영향 제거를 위한 가우시안 블러 처리를 진행
            
            for y in range(0, img_height, pixel_size) :         # 이중 반복문을 통해, 각 그룹마다의 intensity 평균값을 계산
                
                for x in range(0, img_width, pixel_size) :
                    
                    roi_img = blurred_img[y : y + pixel_size, x : x + pixel_size]
                    
                    gray_value = np.mean(roi_img)
                    
                    gray_values.append(gray_value)
            
            gray_values = np.array(gray_values).reshape(img_height // pixel_size, img_width // pixel_size)      # 다시 배열을 reshape
            
            highlighted_image = cv.cvtColor(blurred_img, cv.COLOR_GRAY2BGR)  # 가우시안 블러가 적용된 이미지를 BGR로 확장
            
            highlighted_pixel_count = 0                 
            
            for y in range(1, img_height // pixel_size - 1) :   # 이중 반복문을 통해, 주변 8개의 비교군과 강도값 차이를 계산했을 때, 그 차이가 설정한 임계값을 넘으면 결함으로 감지를 진행
                
                for x in range(1, img_width // pixel_size - 1) :
                    
                    center_pixel_value = gray_values[y, x]
                    
                    surrounding_values = gray_values[y-1 : y+2, x-1 : x+2].flatten()

                    if np.any(np.abs(center_pixel_value - surrounding_values) > diff_threshold):
                        
                        highlighted_image[y * pixel_size:(y + 1) * pixel_size, x * pixel_size:(x + 1) * pixel_size] = [0, 0, 255]
                        
                        highlighted_pixel_count += 1
            
            # 이미지 그리드 나누기 (optional한 과정) : for 문 두개로 구성
            for i in range(0, img_height, grid_size) :
                
                cv.line(highlighted_image, (0, i), (img_width, i), (0, 255, 0), 1)
                
            for j in range(0, img_width, grid_size) :
                
                cv.line(highlighted_image, (j, 0), (j, img_height), (0, 255, 0), 1)
            
            self.eval_img_list.append(highlighted_image)        # 각 위치에서의 샘플에 대해 평가한 이미지를 새로운 리스트에 저장
            
        timestamp = timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        
        filename = f"./image_evaluation/{timestamp}.png"
            
        cv.imwrite(filename, np.vstack(self.eval_img_list))     # 새로운 리스트의 데이터를 세로로 이어서 최종 이미지를 저장
        
        height, width, _ = np.vstack(self.eval_img_list).shape  # 최종적인 sample의 grading 과정 
        
        print("\n-------------- 샘플 그레이드 평과 결과 --------------\n")
        
        for part_number in range(1, 6) :
            
            part_start = (part_number - 1) * (height // 5)
            part_end = part_number * (height // 5)

            part_image = np.vstack(self.eval_img_list)[part_start:part_end, :]
            part_highlighted_count = np.sum(part_image[:, :, 2] == 255)
            part_highlighted_ratio = part_highlighted_count / ((height // 5) * width // pixel_size)

            print(f'Part {part_number}: 하이라이트된 비율 = {part_highlighted_ratio * 100:.2f}%')

            if (part_highlighted_ratio > 0) : dcount = 1
                
            overall_score -= dcount * weights[part_number]
            
            dcount = 0

            overall_score = max(overall_score, 0)

        overall_grade = ''
        
        if overall_score >= 90 : overall_grade = 'A'
            
        elif 70 <= overall_score < 90 : overall_grade = 'B'
            
        elif 50 <= overall_score < 70 : overall_grade = 'C'
            
        else : overall_grade = 'D'

        print(f'\n점수: {overall_score:.2f}, 샘플 등급: {overall_grade}')
            
    
    def save_org_sample(self) :                                 # 원본 이미지를 합친 하나의 이미지 / 평가된 이미지를 합친 하나의 이미지를 저장하는 함수 (optional)
            
        timestamp = timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            
        filename = f"./image_evaluation/{timestamp}.png"
            
        cv.imwrite(filename, np.vstack(self.org_img_list))
       
       
    def stop_cam(self) :                                    # 카메라 프로세스의 종료 조건을 결정하는 함수
        
        self.terminate = True 
            
        self.org_img_list  = []                             # 각 리스트를 초기화
        
        self.eval_img_list = []
                

if __name__ == "__main__" :
    
    communication = communicate()           # 파이썬/아두이노 MCU 간의 통신 class
    
    cont = control()                        # 모터 구동 및 웹캠 thread와의 정보 공유를 위한 class

    cam = webcam()                          # 웹캠 프레임 받아오기 및 이미지 저장을 위한 class

    webcam_thread = threading.Thread(target = cam.capture_img)      # multithread 구조 : 카메라는 병렬적으로 돌림
    
    webcam_thread.start()                   # 웹캠 thread 연산 시작

    input("\nPRESS ENTER TO START THIS PROGRAM ...!")   # 웹캠이 먼저 준비가 되면, 사용자의 입력으로 프로그램 시작

    try :
        
        while True :
            
            cont.move_motor()               # 모터가 한바퀴를 돌고 다시 돌아오기 전까지는 계속 구동을 진행
            
            if cont.motor_loc == 0 : break  
        
    finally :                               # 샘플에 대한 이미지 처리가 완료되는 경우
        
        cam.save_org_sample()               # 샘플의 원본 결과 저장 
        
        cam.evaluate_sample()               # 품질 평가 진행 및 평가 결과 저장
        
        cam.stop_cam()                      # 카메라 thread 종료조건 설정
        
        webcam_thread.join()                # 카메라 thread 종료
        
        arduino.close()                     # serial 통신 종료
        
        print("\n\nPROGRAM TERMINATED ...!")
        
        print("\nSERIAL COMMUNICATION DISCONNECTED ...!\n")
