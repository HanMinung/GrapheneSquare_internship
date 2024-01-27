int step = 2;
int dir = 5;
int steps = 166;
char input;
bool isMoving = false;
int currentPosition = 0;
void setup(){
  pinMode(step, OUTPUT);
  pinMode(dir, OUTPUT);

  digitalWrite(step, LOW);
  digitalWrite(dir, LOW);

  Serial.begin(9600);
  delay(1000);
}

void motorMove(char input){
  isMoving = true;
  if((input == '1') ||  (input == '2') || (input == '3') || (input == '4')){
    for(int j=0; j<steps; j++){
      for(int i=0; i<200; i++){
        digitalWrite(dir, LOW);
        digitalWrite(step, HIGH);
        delayMicroseconds(30);   // 30일때 * 20  // 50일때  * 500/37
        digitalWrite(step, LOW);
        delayMicroseconds(30);
      }
    }
    delay(100);    
  }
  else if(input == '0'){
    for(int j=0; j<steps*4; j++){
      for(int i=0; i<200; i++){
        digitalWrite(dir, HIGH);
        digitalWrite(step, HIGH);
        delayMicroseconds(30);   // 30일때 * 20  // 50일때  * 500/37
        digitalWrite(step, LOW);
        delayMicroseconds(30);
      }
    }
    delay(100);    
  }
  else if(input == 'b'){
    for(int j=0; j<steps*1; j++){
      for(int i=0; i<200; i++){
        digitalWrite(dir, HIGH);
        digitalWrite(step, HIGH);
        delayMicroseconds(30);   // 30일때 * 20  // 50일때  * 500/37
        digitalWrite(step, LOW);
        delayMicroseconds(30);
      }
    }
  }
  else if(input == '<'){
    for(int i=0; i<5*200; i++){
      digitalWrite(dir, HIGH);
      digitalWrite(step, HIGH);
      delayMicroseconds(30);   // 30일때 * 20  // 50일때  * 500/37
      digitalWrite(step, LOW);
      delayMicroseconds(30);
    }
  }
  else if(input == '>'){
    for(int i=0; i<5*200; i++){
      digitalWrite(dir, LOW);
      digitalWrite(step, HIGH);
      delayMicroseconds(30);   // 30일때 * 20  // 50일때  * 500/37
      digitalWrite(step, LOW);
      delayMicroseconds(30);
    }
  }
}

void loop(){
  if (Serial.available() > 0) {
    char input = Serial.read();
    motorMove(input);
    delay(100);
    isMoving = false;
  }
}
