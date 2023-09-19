import datetime
from django.views import View, generic
from django.http import JsonResponse, HttpResponseRedirect
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

from django.http import HttpResponseRedirect
from .forms import CategoryForm, ProductForm, DeleteCategoryForm, DeleteProductForm, ADCustomUserForm, DeleteCustomUserForm, CustomUserDetailForm
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView

class HomeView(View):
    def get(self, request):
        return render(request, 'homepage/index.html')

class CategoryView(generic.DetailView):
    model=Category

    def get(self, request):
        menu = Category.objects.all()
        products = Product.objects.all()
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

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user = request.user
    cart, created = Cart.objects.get_or_create(user=user)

    # Kiểm tra xem sản phẩm đã tồn tại trong giỏ hàng chưa, nếu có thì tăng số lượng
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('/cart')

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

#views cho quản lý đơn hàng
@staff_member_required
def admin_order(request):
    return render(request, 'admin/order.html')

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
