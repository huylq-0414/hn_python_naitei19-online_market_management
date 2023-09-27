import datetime
from django.views import View, generic
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import Category, Product, Cart, CartItem, CustomUser, Order, OrderDetail
from .forms import CustomUserForm, RegistrationForm, CategoryForm, ProductForm, DeleteCategoryForm
from django.contrib.auth import logout
from djmoney.money import Money
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.http import HttpResponseRedirect
from .forms import CategoryForm, ProductForm, DeleteCategoryForm, DeleteProductForm, ADCustomUserForm, DeleteCustomUserForm, CustomUserDetailForm
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView
import datetime
from datetime import date
from unidecode import unidecode
from django.db.models.functions import TruncDate, Trunc
from django.utils import timezone
from django.db.models import Sum, Count

class HomeView(View):
    def get(self, request):
        return render(request, 'homepage/index.html')

class CategoryView(generic.DetailView):
    model=Category

    def get(self, request):
        menu = Category.objects.all()
        products = Product.objects.all().order_by('name')
        if request.GET.get('food_name'):
            productssearch =  filter(lambda x: unidecode((request.GET.get('food_name'))).lower()  in unidecode((_(x.name))).lower()  , products)
            return render(request, 'catalog/menu.html', {'menu': menu,'products' : productssearch})
        return render(request, 'catalog/menu.html', {'menu': menu,'products' : products})

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = CustomUserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Changes saved'))
            return redirect('/profile')  # Sử dụng tên URL 'profile' để chuyển hướng

    else:
        form = CustomUserForm(instance=request.user)

    return render(request, 'registration/profile.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('login')

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            cart = Cart.objects.create(user=user)
            cart.save()
            # Xử lý sau khi đăng ký thành công, ví dụ: chuyển hướng đến trang đăng nhập
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

class CartView(View):
    model=Cart

    def get(self, request):
        cartall = CartItem.objects.filter(cart_id=Cart.objects.get(user_id=request.user.id))
        total_price = sum(item.product.base_price * item.quantity for item in cartall)
        return render(request, 'catalog/cart.html',{'cartall': cartall,'total_price': total_price})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user = request.user
    cart, created = Cart.objects.get_or_create(user=user)

    # Kiểm tra xem sản phẩm đã tồn tại trong giỏ hàng chưa, nếu có thì tăng số lượng
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('/category')

@login_required
def update_cart(request):

    if request.method == 'POST':
        action = request.POST.get('action')
        status = -1
        try:
            cart = CartItem.objects.get(id=request.POST.get("cart_item_id"))
            if (action=='increase'):
                cart.quantity += 1
            elif (action == 'decrease'):
                cart.quantity -= 1
            cart.save()
            status = 1
            if (action == 'delete') or (cart.quantity<1):
                cart.delete()
                status = 2
            cartall = CartItem.objects.filter(cart_id=Cart.objects.get(user_id=request.user.id))
            total_price = sum(item.product.base_price * item.quantity for item in cartall)
            return JsonResponse({'status': status,'message': 'Cập nhật giỏ hàng thành công', 'quantity': cart.quantity,'total_price': total_price})
            
        except Cart.DoesNotExist:
            return JsonResponse({'status': -1,'message': 'Sản phẩm không tồn tại'}, status=404)
    else:
        return JsonResponse({'status': -1,'message': 'Yêu cầu không hợp lệ'}, status=400)

#views cho quản lý thể loại
@method_decorator(staff_member_required, name='dispatch')
class AdminCategoryList(ListView):
    model = Category
    template_name = 'admin/category_list.html'
    context_object_name = 'categories'
    paginate_by = 5

    ordering = ['name']

@staff_member_required 
def delete_categories(request):
    if request.method == 'POST':
        form = DeleteCategoryForm(request.POST)
        if form.is_valid():
            category_ids = form.cleaned_data['category_ids']
            Category.objects.filter(id__in=category_ids).delete()
            return redirect('home:admin_category_list')
    else:
        form = DeleteCategoryForm()

    categories = Category.objects.all()
    return render(request, 'category_list.html', {'categories': categories, 'form': form})

@staff_member_required
def admin_category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('home:admin_category_list'))
    else:
        form = CategoryForm()
    return render(request, 'admin/category_form.html', {'form': form})

@staff_member_required
def admin_category_update(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('admin_category_list'))
    else:
        form = CategoryForm(instance=category)
    return render(request, 'admin/category_form.html', {'form': form})

@staff_member_required
def admin_category_detail(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    categories = Category.objects.all().order_by('name')
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _('Changes saved'))
            return redirect('home:admin_category_detail', category_id=category_id)
    else:
        form = CategoryForm(instance=category)
    return render(request, 'admin/category_detail.html', {'category': category, 'categories': categories, 'form': form})

#views cho quản lý sản phẩm
@method_decorator(staff_member_required, name='dispatch')
class AdminProductList(ListView):
    model = Product
    template_name = 'admin/product_list.html'
    context_object_name = 'products'
    paginate_by = 5

    def get_queryset(self):
        return Product.objects.select_related('category').order_by('category__name', 'name')

@staff_member_required
def admin_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('home:admin_product_list'))
    else:
        form = ProductForm()
    return render(request, 'admin/product_form.html', {'form': form})

@staff_member_required
def admin_product_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('admin_product_list'))
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin/product_form.html', {'form': form})

@staff_member_required
def delete_products(request):
    if request.method == 'POST':
        form = DeleteProductForm(request.POST)
        if form.is_valid():
            product_ids = form.cleaned_data['product_ids']
            Product.objects.filter(id__in=product_ids).delete()
            return redirect('home:admin_product_list')
    else:
        form = DeleteProductForm()
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products, 'form': form})

@staff_member_required
def admin_product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    products = Product.objects.all().order_by('name')
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, _('Changes saved'))
            return redirect('home:admin_product_detail', product_id=product_id)
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin/product_detail.html', {'product': product, 'products': products, 'form': form})

class OrderView(View):
    model = Order

    def get(self, request):
        try:
            cart = Cart.objects.get(user_id=request.user.id)
            cartall = CartItem.objects.filter(cart_id=cart)
            total_price = sum(item.product.base_price * item.quantity for item in cartall)
        except Cart.DoesNotExist:
            # Xử lý khi không tìm thấy giỏ hàng
            cartall = []
            total_price = 0
            
        return render(request, 'catalog/order.html', {'cartall': cartall, 'total_price': total_price})

@transaction.atomic
def add_order(request):
    user = request.user
    cart = get_object_or_404(Cart, user=user)
    order = Order(cart=cart, user=user)
    order.save()
    cartall = CartItem.objects.filter(cart=Cart.objects.get(user=user))  
    try:
        # Bắt đầu một transaction
        with transaction.atomic():
            for cartitem in cartall:
                order_detail = OrderDetail(
                    price=cartitem.product.base_price,
                    quantity=cartitem.quantity,
                    total_cost=cartitem.product.base_price * cartitem.quantity,
                    order=order,
                    product=cartitem.product
                )
                order_detail.save()
                cartitem.delete()

            order.status = 0
            order.save()
    except Exception as e:
        # Xử lý lỗi nếu có
        transaction.rollback()
        # Ghi log lỗi hoặc thông báo lỗi tùy theo nhu cầu
        print(f"Transaction failed: {str(e)}")
class OrderView(View):
    model = Order

    def get(self, request):
        try:
            cart = Cart.objects.get(user_id=request.user.id)
            cartall = CartItem.objects.filter(cart_id=cart)
            total_price = sum(item.product.base_price * item.quantity for item in cartall)
        except Cart.DoesNotExist:
            cartall = []  # Không tìm thấy bản ghi Cart, danh sách cartall rỗng
            total_price = 0

        return render(request, 'catalog/order.html', {'cartall': cartall, 'total_price': total_price})

def search_food(request):
    menu = Category.objects.all()
    products = Product.objects.all()
    return render(request, 'catalog/menu.html', {'menu': menu, 'products': products})

@login_required
def add_order(request):
    user = request.user
    cart = get_object_or_404(Cart, user=user)

    if cart:
        # Sử dụng transaction.atomic() để đảm bảo tính toàn vẹn dữ liệu
        with transaction.atomic():
            order = Order(cart=cart, user=user)
            order.save()
            
            cartall = CartItem.objects.filter(cart=cart)
            # Thêm các chi tiết đơn hàng vào trong giao dịch
            for cartitem in cartall:
                order_detail = OrderDetail(
                    price=cartitem.product.base_price,
                    quantity=cartitem.quantity,
                    total_cost=cartitem.product.base_price * cartitem.quantity,
                    order=order,
                    product=cartitem.product)
                order_detail.save()            
                order.order_cost += order_detail.total_cost
                cartitem.delete()

            order.status = 0
            order.save()

    return redirect('/yourorder/')

class YourOrderView(View):
    model=Order

    def get(self, request):
        orders = Order.objects.filter(user=request.user, status__lt=2).order_by('-order_date')
        orderAllItem=[]
        for order in orders :
            orderall = OrderDetail.objects.filter(order = order) 
            total_price = sum(item.price * item.quantity for item in orderall)
            order_date = order.order_date + datetime.timedelta(hours=7)
            formatted_date = order_date.strftime("%H:%M:%S %d-%m-%Y")
            orderAllItem.append({'allItem':orderall,'total_price':total_price,'order':order,'formatted_date':formatted_date})
        return render(request, 'catalog/yourorder.html',{'orderAllItem': orderAllItem,'total_price': total_price})

@login_required
def cancelled_order(request, order_id):
    user = request.user
    order = get_object_or_404(Order, user=user, id=order_id, status__lt=2)
    if order.status<2 :
        order.status = 2
        order.save()
        return redirect('/yourorder/')
    else:
        return HttpResponse("Không thể hủy đơn hàng này vì đã được xử lý hoặc đã hoàn thành.")
    
#views cho quản lý người dùng
@method_decorator(staff_member_required, name='dispatch')
class AdminUserList(ListView):
    model = CustomUser
    template_name = 'admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 5


@staff_member_required
def admin_user_create(request):
    if request.method == 'POST':
        form = ADCustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('home:admin_user_list'))
    else:
        form = ADCustomUserForm()
    return render(request, 'admin/user_form.html', {'form': form})

@staff_member_required
def delete_users(request):
    if request.method == 'POST':
        form = DeleteCustomUserForm(request.POST)
        if form.is_valid():
            user_ids = form.cleaned_data['user_ids']
            CustomUser.objects.filter(id__in=user_ids).delete()
            return redirect('home:admin_user_list')
    else:
        form = DeleteCustomUserForm()
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users, 'form': form})

@staff_member_required
def admin_user_detail(request, user_id):
    aduser = get_object_or_404(CustomUser, pk=user_id)
    users = CustomUser.objects.all()
    if request.method == 'POST':
        form = CustomUserDetailForm(request.POST, instance=aduser)
        if form.is_valid():
            aduser = form.save(commit=False)
            aduser.is_staff = form.cleaned_data['is_staff']
            aduser.save()
            messages.success(request, _('Changes saved'))
            return redirect('home:admin_user_detail', user_id=user_id)
    else:
        form = CustomUserDetailForm(instance=aduser)
    return render(request, 'admin/user_detail.html', {'aduser': aduser, 'users': users, 'form': form})

#views cho quản lý order
@method_decorator(staff_member_required, name='dispatch')
class AdminOrderList(View):
    model = Order

    def get(self, request, status=None):
        if status is None:
            # Nếu không có trạng thái được chỉ định, mặc định là 'all'
            status = 'all'

        orders = Order.objects.order_by('-order_date')
        orderAllItem = []

        for order in orders:
            orderall = OrderDetail.objects.filter(order=order)
            total_price = sum(item.price * item.quantity for item in orderall)
            naive_order_date = datetime.datetime(2023, 9, 28, 12, 0, 0)
            aware_order_date = timezone.make_aware(naive_order_date, timezone.get_default_timezone())
            local_order_date = timezone.localtime(aware_order_date)
            formatted_date = local_order_date.strftime("%H:%M:%S %d/%m/%Y")

            if status == 'all' or order.status == status:
                orderAllItem.append({'allItem': orderall, 'total_price': total_price, 'order': order, 'formatted_date': formatted_date})

        return render(request, 'admin/order_list.html', {'orderAllItem': orderAllItem, 'total_price': total_price, 'status': status})

@staff_member_required
def accept_order(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        order.status = 1
        order.save()
        return redirect('home:admin_order')
    except Order.DoesNotExist:
        return HttpResponse(_('Đơn đặt hàng không tồn tại'), status=404)

@staff_member_required
def reject_order(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        order.status = 3
        order.save()
        return redirect('home:admin_order')
    except Order.DoesNotExist:
        return HttpResponse(_('Đơn đặt hàng không tồn tại'), status=404)

@staff_member_required
def delete_order(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        if order.status in [2, 3, 4]:
            order.delete()
            return redirect('home:admin_order')
        else:
            return HttpResponse(_('Không thể xóa đơn đặt hàng với trạng thái này'), status=400)
    
    except Order.DoesNotExist:
        return HttpResponse(_('Đơn đặt hàng không tồn tại'), status=404)
@login_required
def cancelled_order(request, order_id):
    user = request.user
    order = get_object_or_404(Order, user=user, id=order_id)
    order.status = 3
    order.save()
    return redirect('/yourorder/')

# View dành cho thống kê
class Statistics(ListView):
    model = Order
    template_name = 'admin/statistics.html'
    paginate_by = 5
    
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        date_status=0
        today = date.today()

        if start_date and end_date:
            if(start_date>=end_date):
                date_status=0
            else:
                date_status=1
        # Kiểm tra xem start_date có giá trị không rỗng
        daily_order_totals = Order.objects.filter(status=4)
        if start_date:
            daily_order_totals = daily_order_totals.filter(order_date__gte=start_date)
        # Áp dụng điều kiện cho end_date
        if end_date:
            daily_order_totals = daily_order_totals.filter(order_date__lt=end_date)

        daily_order_totals = daily_order_totals.annotate(
            order_date_new=Trunc('order_date','day')
        ).values('order_date_new').annotate(
            total_price=Sum('order_cost'),
            count=Count('id')
        ).order_by('order_date_new')
        
        daily_summary = daily_order_totals.filter(order_date__gte=today)
        daily_summary = daily_summary.annotate(
            order_today_new=Trunc('order_date','day')
        ).values('order_today_new').annotate(
            total_price=Sum('order_cost'),
            count=Count('id')
        )

        return render(request, 'admin/statistics.html',{
            'daily_summary': daily_summary,
            'today': today,
            'orderAllItem': daily_order_totals,
            'start_date': start_date,
            'end_date': end_date, 
            'date_status': date_status})
