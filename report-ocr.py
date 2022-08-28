import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import sys,json
import base64
import random,time
from Crypto.Cipher import AES
import muggle_ocr
import traceback

def push(Text,email):
    if email !='':
        url=url='https://prod-168.westus.logic.azure.com:443/workflows/363a7520f4ed4aa49b66d671d557d05c/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=IifAnYntQOWrsMgoRbi4f8uqzProrcU9E91xzjg42AM'
        date={"user":email,"title":"健康打卡通知","msg":Text}
        r = requests.post(url,json=date).text;print(r)
class Utils: 
    logs=''
    @staticmethod
    def getTime(Mod='%Y-%m-%d %H:%M:%S', offset=0):
        utc_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
        bj_dt = utc_dt.astimezone(timezone(timedelta(hours=8)))
        bj_dt = bj_dt-timedelta(days=offset)
        return bj_dt.strftime(Mod)
    @staticmethod           
    def log(content):
        Text = Utils.getTime() + ' ' + str(content)
        print(Text)
        Utils.logs = Utils.logs+'<br>'+Text
        sys.stdout.flush()
    @staticmethod    
    def randString(length):
        baseString = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"
        data = ''
        for i in range(length):
            data += baseString[random.randint(0, len(baseString) - 1)]
        return data
    @staticmethod    
    def encryptAES(data, key):
        ivStr = '\x01\x02\x03\x04\x05\x06\x07\x08\x09\x01\x02\x03\x04\x05\x06\x07'
        aes = AES.new(bytes(key, encoding='utf-8'), AES.MODE_CBC,bytes(ivStr, encoding="utf8"))
        text_length = len(data)
        amount_to_pad = AES.block_size - (text_length % AES.block_size)
        if amount_to_pad == 0:
            amount_to_pad = AES.block_size
        pad = chr(amount_to_pad)
        data = data + pad * amount_to_pad
        text = aes.encrypt(bytes(data, encoding='utf-8'))
        text = base64.encodebytes(text)
        text = text.decode('utf-8').strip()
        return text
    
   
class Work():
    def __init__(self,user):
        self.username=user['username']
        self.password=user['password']
        self.email=user.get('email','')
        self.session=requests.session()
        self.headers={
            'User-Agent':'Mozilla/5.0(Linux;U;Android11;zh-CN;RedmiK30ProBuild/RKQ1.200826.002)AppleWebKit/537.36(KHTML,likeGecko)Version/4.0Chrome/69.0.3497.100UWS/3.22.1.161MobileSafari/537.36AliApp(DingTalk/6.3.25)com.alibaba.android.rimet/22868778Channel/700159language/zh-CNabi/64UT4Aplus/0.2.25colorScheme/light',
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }
        self.session.headers=self.headers
        self.Trytimes=0
    
    def login(self):
        url="https://ids.cqupt.edu.cn/authserver/login?service=http://ehall.cqupt.edu.cn/publicapp/sys/cyxsjkdkmobile/*default/index.html"
        html=self.session.get(url=url,allow_redirects=False);Timestamp=int(time.time()*1000)
        soup = BeautifulSoup(html.text,'lxml')
        salt = soup.select("#pwdEncryptSalt");salt = salt[0].get('value')
        form = soup.select('input');params={}
        for item in form:
            if None != item.get('name') and len(item.get('name')) > 0:
                if item.get('name') != 'rememberMe':
                    if None == item.get('value'):
                        params[item.get('name')] = ''
                    else:
                        params[item.get('name')] = item.get('value')
        params['username']=self.username
        params['password']=Utils.encryptAES(Utils.randString(64) + self.password, salt)
        Captcha =self.session.get(url=f'https://ids.cqupt.edu.cn/authserver/getCaptcha.htl?{Timestamp}')
        sdk = muggle_ocr.SDK(model_type = muggle_ocr.ModelType.Captcha)
        params['captcha'] =sdk.predict(image_bytes = Captcha.content)
        try:
            res=self.session.post(url=url,params=params,allow_redirects=False)
            if res.status_code ==302:
                self.session.get(res.headers['Location']);self.session.get(url='http://ehall.cqupt.edu.cn/publicapp/sys/cyxsjkdk/getUserId.do')
                self.session.get(url='http://ehall.cqupt.edu.cn/publicapp/sys/funauthapp/api/getAppConfig/cyxsjkdkmobile-6578524306216816.do?GNFW=MOBILE')
                Utils.log(f"账号{self.username}登录成功");return True
        except Exception as e:
            print(f'错误日志如下：\n[{e}]\n{traceback.format_exc()}')
        Utils.log('账号登录失败')
        return None  
        
    def sign(self):
        #self.session.get(url='http://ehall.cqupt.edu.cn/publicapp/sys/cyxsjkdk/modules/yddjk/T_XSJKDK_XSTBXX_QUERY.do').json()
        Info=self.session.get(url='http://ehall.cqupt.edu.cn/publicapp/sys/cyxsjkdk/modules/yddjk/T_XSJKDK_XSTBXX_QUERY.do').json()['datas']['T_XSJKDK_XSTBXX_QUERY']['rows']
        Info=sorted(Info,key=lambda keys: keys['RQ'],reverse=True);form=None
        if Info[0]['SFDK']=='是':
            Utils.log("检测到今日打卡已完成")
        else:
            for info in Info:
                if info['SFDK']=='是':
                    form=info;information=Info[0]
                    Utils.log(f"获取到{info['DKSJ']}提交的打卡信息");break
            if  form!=None:
                Form={'WID':information['WID'],'RQ':information['RQ'],'DKSJ':Utils.getTime()};form.update(Form)
                try:
                    r=self.session.get(url='http://ehall.cqupt.edu.cn/publicapp/sys/cyxsjkdk/modules/yddjk/T_XSJKDK_XSTBXX_SAVE.do',params=form).json()['datas']['T_XSJKDK_XSTBXX_SAVE']
                    Utils.log(f"打卡提交成功，提交的地址为{form['MQJZD']} {form['JZDXXDZ']}(如需更新请手动完成一次提交)")
                except Exception as e:
                    Utils.log('打卡提交失败')
                    print(f'日志如下：\n[{e}]\n{traceback.format_exc()}')
            else:
                Utils.log("近七天内无打卡记录，请手动完成本次打卡")
        return None
    def work(self):
        while self.Trytimes < 3:
            self.Trytimes += 1 
            try:
                if self.login():
                    self.sign();break
            except:
                continue        
        push(Utils.logs,self.email)

def main():
    try:
        with open("userinfo.json", "r") as f:
            userinfo= json.load(f)
            for user in userinfo:
                if user['username'] and user['password']:
                    wk=Work(user);wk.work()
                else:
                    print("请前往userinfo.json文件中配置用户信息")
                Utils.logs=''
        f.close()        
    except:
        print("请确保userinfo.json文件与当前文件在同一路径")

if __name__ == "__main__":
    main()
    

      
def handler(event, context):
    main()