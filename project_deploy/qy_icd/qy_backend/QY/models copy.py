from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import datetime
import uuid

# Create your models here.

class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")

    def __str__(self):
        return self.question_text

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text


# 创建一个特定PDF的OCR数据识别的数据保存
class PDFOCRData(models.Model):
    # 基础
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 文档信息
    filename = models.CharField("文件名", max_length=255)
    file_path = models.CharField("文件地址", max_length=1024)
    raw_text = models.TextField("原始文本", blank=True, null=True)

    # 结构化字段
    personal_history = models.TextField("个人史", blank=True, null=True)
    chief_complaint = models.TextField("主诉", blank=True, null=True)
    inpatient_no = models.CharField("住院号", max_length=100, blank=True, null=True)
    admission_status = models.TextField("入院情况", blank=True, null=True)
    admission_diagnosis = models.TextField("入院诊断", blank=True, null=True)
    discharge_diagnosis = models.TextField("出院诊断", blank=True, null=True)
    marital_history = models.TextField("婚姻史", blank=True, null=True)
    family_history = models.TextField("家族史", blank=True, null=True)
    imaging_opinion = models.TextField("影像学意见", blank=True, null=True)
    operation_name = models.CharField("手术名称", max_length=255, blank=True, null=True)
    operation_course = models.TextField("手术经过", blank=True, null=True)
    past_history = models.TextField("既往史", blank=True, null=True)
    intraoperative_diagnosis = models.TextField("术中诊断", blank=True, null=True)
    present_illness = models.TextField("现病史", blank=True, null=True)
    case_identifier = models.CharField("病案标识", max_length=255, blank=True, null=True)
    course_record = models.TextField("病程记录", blank=True, null=True)
    treatment_course = models.TextField("诊疗经过", blank=True, null=True)
    ultrasound_impression = models.TextField("超声印象", blank=True, null=True)
    ultrasound_hint = models.TextField("超声提示", blank=True, null=True)

    class Meta:
        verbose_name = "PDF OCR 数据"
        verbose_name_plural = "PDF OCR 数据"

    def __str__(self):
        return f"{self.filename}"

class V_Patient_Surgery(models.Model):
    """
    手术表 Surgery
    对应表结构：
    - id            主键ID，自增
    - case_id       病案标识号，varchar(50)
    - surgery_seq   手术序号，主手术为1
    - surgery_code  手术编码，varchar(50)
    - surgery_name  手术名称，varchar(200)
    """

    # id 字段 Django 会自动生成：AutoField(primary_key=True)

    case_id = models.CharField(
        max_length=50,
        verbose_name="病案标识号",
        help_text="住院号/病案号",
    )
    surgery_seq = models.IntegerField(
        verbose_name="手术序号",
        help_text="手术顺序号，主手术为1",
    )
    surgery_code = models.CharField(
        max_length=50,
        verbose_name="手术编码",
        help_text="关联手术编码字典库",
    )
    surgery_name = models.CharField(
        max_length=200,
        verbose_name="手术名称",
        help_text="关联手术名称字典库",
    )

    class Meta:
        verbose_name = "手术"
        verbose_name_plural = "手术"
        ordering = ["case_id", "surgery_seq", "id"]

    def __str__(self):
        # 带上编码信息，方便区分
        return f"{self.case_id}-{self.surgery_seq}-{self.surgery_code}-{self.surgery_name}"

class V_Patient_Diagnosis(models.Model):
    """
    诊断表 Diagnosis
    对应表结构：
    - id         主键ID，自增
    - case_id    病案标识号，varchar(50)
    - diag_type  诊断类型，varchar(20)，枚举：出院诊断 / 损伤中毒 / 病理诊断
    - diag_seq   诊断序号，int，主诊断=1
    - diag_code  诊断编码，varchar(50)
    - diag_name  诊断名称，varchar(200)
    """

    class DiagnosisType(models.TextChoices):
        DISCHARGE = "出院诊断", "出院诊断"
        INJURY_POISON = "损伤中毒", "损伤中毒"
        PATHOLOGICAL = "病理诊断", "病理诊断"
    
    case_id = models.CharField(
        max_length=50,
        verbose_name="病案标识号",
        help_text="住院号/病案号",
    )
    diag_type = models.CharField(
        max_length=20,
        choices=DiagnosisType.choices,
        verbose_name="诊断类型",
        help_text="枚举：出院诊断 / 损伤中毒 / 病理诊断",
    )
    diag_seq = models.IntegerField(
        verbose_name="诊断序号",
        help_text="诊断顺序号，主诊断=1",
    )
    diag_code = models.CharField(
        max_length=50,
        verbose_name="诊断编码",
        help_text="关联诊断编码字典库",
    )
    diag_name = models.CharField(
        max_length=200,
        verbose_name="诊断名称",
        help_text="关联诊断名称字典库",
    )

    class Meta:
        verbose_name = "诊断"
        verbose_name_plural = "诊断"
        ordering = ["case_id", "diag_type", "diag_seq"]

    def __str__(self):
        return f"{self.case_id}-{self.diag_type}-{self.diag_seq}-{self.diag_code}-{self.diag_name}"
    
# 用户信息
class UserProfile(models.Model):
    """
    千医用户扩展信息：
    - role: 管理员0 / 普通用户1
    - real_name: 真实姓名
    - phone: 手机号
    - status: 0 禁用 / 1 启用
    """
    ROLE_ADMIN = 0
    ROLE_USER = 1
    ROLE_CHOICES = (
        (ROLE_ADMIN, "管理员"),
        (ROLE_USER, "普通用户"),
    )

    STATUS_DISABLED = 0
    STATUS_ENABLED = 1
    STATUS_CHOICES = (
        (STATUS_DISABLED, "禁用"),
        (STATUS_ENABLED, "启用"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.IntegerField(choices=ROLE_CHOICES, default=ROLE_USER)
    real_name = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_ENABLED)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.real_name or self.user.username

# 聊天记录 
class ChatHistory(models.Model):
    TYPE_CHOICES = (
        ('coding', '智能病案编码'),
        ('knowledge', '疾病手术知识查询'),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # 关联用户，确保只能看到自己的记录
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_histories')
    # 区分业务类型
    chat_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    # 标题
    title = models.CharField(max_length=100, blank=True, null=True)
    # 核心数据：存储完整的对话JSON结构 (questList, answerList 等)
    data = models.JSONField(default=dict, blank=True)
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at'] # 默认按更新时间倒序
        verbose_name = '聊天记录'
        verbose_name_plural = '聊天记录'

    def __str__(self):
        return f"{self.user.username} - {self.get_chat_type_display()} - {self.title}"

class Feedback(models.Model):
    """
    用户反馈表
    存储用户对表格行数据的点赞/点踩及备注信息
    """
    TYPE_LIKE = 'like'
    TYPE_DISLIKE = 'dislike'
    TYPE_CHOICES = (
        (TYPE_LIKE, '点赞'),
        (TYPE_DISLIKE, '点踩'),
    )

    # 关联用户
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    
    # 关联聊天记录 (可选，建议加上以便追溯是在哪次对话中产生的反馈)
    # 假设前端能传过来 chat_uuid，如果暂时不能，可以设为 null=True
    chat_history = models.ForeignKey(ChatHistory, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')

    # 反馈类型
    feedback_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # 用户备注内容
    remark = models.TextField("反馈备注", blank=True, null=True)
    
    # 行索引 (虽然可能变动，但作为参考记录)
    row_index = models.IntegerField("行索引", default=0)
    
    # 存储行数据的快照 (建议存JSON，这样无论表格结构怎么变都能存)
    row_data = models.JSONField("行数据快照", default=dict, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '用户反馈'
        verbose_name_plural = '用户反馈'

    def __str__(self):
        return f"{self.user.username} - {self.get_feedback_type_display()} - {self.created_at}"