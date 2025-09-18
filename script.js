// const myBody = document.body;
// myBody.style.backgroundColor = "red";
// console.log(myBody);

// // const box2 = document.getElementById("box-2");
// // console.log(box2);
// const box2 = document.getElementsByTagName("div");
// console.log(box2);

// const boxes = document.getElementsByClassName("container");
// console.log(boxes);

// const random = document.querySelectorAll(".container .random");
// const boxeses = document.getElementsByClassName("box");
// console.log(boxeses);
// for(let i = 0; i<boxeses.length;i++){
//     boxeses[i].classList.add("round-border");
// }

const a = 10;
const b = 20;
sum(a,b);
console.log("sum is", sum(a,b));

const c = 5;
const d = 15;
sum(c,d);
console.log("sum is", sum(c,d));

function sum(a,b){
    const sum = a+b;
    console.log("Result is ", sum);
    return sum;
}

const square = function(num){
    return num*num;
}
console.log("square is", square(10));

function addSquare(a,b){
    const sa = square(a);
    const sb = square(b);
    function square(x){
        return x*x;
    }
    return sa*sb;
}
console.log("add square",addSquare(4,5));

const square2 = num=>num*num;
console.log("square is",square2(3));
const calculate = (a,b,operation)=>{
    return operation(a,b);
}
const addition = calculate(3,4,(num1,num2)=>{
    return num1+num2;
});
console.log(addition);
const subtraction = (a,b)=>  a-b;
const subResult = calculate(8,3,subtraction);
console.log(subResult);
function mul(a,b)
{
    return a*b;
}
const mulres=calculate(10,20,mul);
console.log(mulres)
function getdata(callback)
{
    setTimeout(()=>
    {
        const name="shreyash";
        console.log("your name is",name);
        callback(name);
    },4000);
}
getdata((name)=>
{
    console.log("got the name",name)
});
console.log("I will be executed first");