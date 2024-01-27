from module import *

num_assemble   =   5                            # 합치고자 하는 이미지의 수
delay_time     =   10                           # 모터가 구동하고 이미지를 저장하기 전까지 주는 delay

img_width      =   3840                         # 이미지는 4K로 처리
img_height     =   2160

arduino        = serial.Serial(port = 'COM4', baudrate = 9600)

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
        
        self.cap.set(cv.CAP_PROP_AUTOFOCUS, 0.19)
        
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
        
        if capture_flag and not img_captured :              # 이미지를 한 번만 저장하기 위한 변수            
            
            # 현재 스테이트의 프레임을 리스트에 저장
            if len (self.org_img_list) == 4  :  self.org_img_list.append(self.frame[0 : 1500, 0 : 3840])            
            
            else  :  self.org_img_list.append(self.frame)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")      # 파일명은 현재 시간을 기준으로 저장
        
            filename = f"./image_evaluation/{timestamp}.png" 

            cv.imwrite(filename, self.frame)                # 이미지를 정해진 경로에 저장
            
            capture_flag = False                            # 저장 완료후에는 각 flag들을 초기화
            
            img_captured = True
            
        self.print_state()                                  # 현재 FLAG 들의 정보를 보기 위한 함수
            
    
    def evaluate_sample(self) :                             # 저장된 이미지에 대해 품질 평가를 진행하는 함수
        
        # 픽셀 크기 및 그리그 크기 지정
        pixel_size              =   10
        grid_size               =   60
        diff_threshold          =   6.5
        
        highlighted_pixel_ratio =   0
        total_pixel_ratio       =   0
        
        for img in self.org_img_list :
            
            gray_values = []
            
            gray_img    = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
            
            blurred_img = cv.GaussianBlur(gray_img, (5,5), 0)
            
            for y in range(0, img_height, pixel_size) :
                
                for x in range(0, img_width, pixel_size) :
                    
                    roi_img = blurred_img[y : y + pixel_size, x : x + pixel_size]
                    
                    gray_value = np.mean(roi_img)
                    
                    gray_values.append(gray_value)
            
            gray_values = np.array(gray_values).reshape(img_height // pixel_size, img_width // pixel_size)
            
            highlighted_image = cv.cvtColor(blurred_img, cv.COLOR_GRAY2BGR)  # 가우시안 블러가 적용된 이미지를 BGR로 확장
            
            highlighted_pixel_count = 0
            
            for y in range(1, img_height // pixel_size - 1) :
                
                for x in range(1, img_width // pixel_size - 1) :
                    
                    center_pixel_value = gray_values[y, x]
                    
                    surrounding_values = gray_values[y-1 : y+2, x-1 : x+2].flatten()

                    if np.any(np.abs(center_pixel_value - surrounding_values) > diff_threshold):
                        
                        highlighted_image[y * pixel_size:(y + 1) * pixel_size, x * pixel_size:(x + 1) * pixel_size] = [0, 0, 255]
                        
                        highlighted_pixel_count += 1
                        
            for i in range(0, img_height, grid_size) :
                
                cv.line(highlighted_image, (0, i), (img_width, i), (0, 255, 0), 1)
                
            for j in range(0, img_width, grid_size) :
                
                cv.line(highlighted_image, (j, 0), (j, img_height), (0, 255, 0), 1)
            
            total_pixel_count = (img_height // pixel_size) * (img_width // pixel_size)
            
            highlighted_pixel_ratio = highlighted_pixel_count / total_pixel_count

            total_pixel_ratio += highlighted_pixel_ratio
            
            self.eval_img_list.append(highlighted_image)
        
        timestamp = timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            
        print(f"\n\nDEFECT RATIO IN SAMPLE : {total_pixel_ratio}")
        
        filename = f"./image_evaluation/{timestamp}.png"
            
        cv.imwrite(filename, np.vstack(self.eval_img_list))
        
    
    def save_org_sample(self) :                                 # 원본 이미지를 합친 하나의 이미지 / 평가된 이미지를 합친 하나의 이미지를 저장하는 함수 (optional)
            
        timestamp = timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            
        filename = f"./image_evaluation/{timestamp}.png"
            
        cv.imwrite(filename, np.vstack(self.org_img_list))
       
       
    def stop_cam(self) :                                    # 카메라 프로세스의 종료 조건을 결정하는 함수
        
        self.terminate = True 
            
        self.org_img_list  = []                             # 각 리스트를 초기화
        
        self.eval_img_list = []
    
    def print_state(self) :
            
        self.print_cnt += 1
        
        if self.print_cnt % 30 == 0 :    
            
            print("\n-------------- Flag state ------------\n    ")
            print(f"MOTOR LOCATION  : {self.motor_loc}           ")
            print(f"IMAGE LIST LEN  : {len(self.org_img_list)}   ")
            print(f"CAPTURE FLAG    : {capture_flag}             ")
            print(f"COMPLETE FLAG   : {img_captured}             ")
            print("--------------------------------------        ")
                

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
            
    except KeyboardInterrupt :              # 키보드 입력시 프로그램 종료
        
        print("\nPROGRAM TERMINATED BY USER ...!")
        
    finally :                               # 샘플에 대한 이미지 처리가 완료되는 경우
        
        cam.save_org_sample()               # 샘플의 원본 결과 저장 
        
        cam.evaluate_sample()               # 품질 평가 진행 및 평가 결과 저장
        
        cam.stop_cam()                      # 카메라 thread 종료조건 설정
        
        webcam_thread.join()                # 카메라 thread 종료
        
        arduino.close()                     # serial 통신 종료
        
        print("\nPROGRAM TERMINATED ...!")
        
        print("\nSERIAL COMMUNICATION DISCONNECTED ...!")
